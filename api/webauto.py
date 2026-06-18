#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页自动化采集 API

基于 Playwright（同步 API）实现「可视化点选 + 自动采集」能力。

设计要点：
  - lazy import：模块顶层绝不导入 playwright，全部在方法内部按需导入，
    导入失败时返回友好错误（提示运行 pnpm run init），避免整个 app 崩溃。
  - 线程模型：Playwright 同步对象是线程亲和的，必须在创建它的同一线程里使用。
    因此：
      * 点选会话（pick）在一个独立后台线程里完整跑（启动→开浏览器→注入→等用户→关闭）；
      * 采集任务（run）在另一个独立后台线程里完整跑；
      * 主线程（pywebview 调用的方法）只做：启停线程、读写用锁保护的共享状态。
  - 浏览器内核首次使用自动下载（playwright install chromium，subprocess）。
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.utils import api_error, api_success


# ============================================================================
# 注入到页面的点选脚本（纯 JS）。
# 该脚本会在右上角渲染一个浮层工具条，让用户用鼠标点选：列表块/字段/翻页/详情字段。
# 所有点选结果通过 window.__ppxEvent(payload) 回调到 Python 侧。
# ============================================================================
_PICK_SCRIPT = r"""
(function () {
  function plog(m){ try { console.log('[PPXBAR] ' + m); } catch (e) {} }

  // 安装入口：document-start 注入时文档根节点可能尚未生成（documentElement 为 null），
  // 此时挂载会抛 null.appendChild。boot() 先做就绪判断，未就绪则定时自重试，直到能安全
  // 挂载为止——避免“某次注入时机太早 → 之后再无注入”导致页面跳转 / CF 验证等场景下工具条
  // 装不上或消失。只有真正进入 install() 才置 installed 标志。
  function boot() {
    plog('boot: installed=' + !!window.__ppxPickerInstalled + ' readyState=' + document.readyState + ' hasBody=' + !!document.body + ' hasDocEl=' + !!document.documentElement + ' url=' + location.href);
    if (window.__ppxPickerInstalled) {
      if (window.__ppxRenderToolbar) { try { window.__ppxRenderToolbar(); } catch (e) {} }
      return;
    }
    if (!document.documentElement) { plog('no documentElement yet -> retry in 50ms'); setTimeout(boot, 50); return; }
    install();
  }

  function install() {
    window.__ppxPickerInstalled = true;
    plog('installing at readyState=' + document.readyState + ' hasBody=' + !!document.body);

  // ----- 共享状态 -----
  var state = {
    mode: 'container',     // container | field | pagination | detailField
    container: '',         // 列表块选择器
    fields: [],            // [{id,name,selector,attr,sample}]
    pagination: '',        // 翻页按钮选择器
    detailFields: [],      // 详情字段
    detailLinkField: ''    // 用户进入详情时所用字段名（在字段模式点击 a 进入详情时记录）
  };
  window.__ppxState = state;
  var seq = 0;

  // ----- 样式 -----
  var style = document.createElement('style');
  style.textContent = [
    '.__ppx_hover{outline:2px solid #ff5722 !important;outline-offset:-1px !important;cursor:crosshair !important;background:rgba(255,87,34,0.08) !important;}',
    '.__ppx_match{outline:2px dashed #2196f3 !important;outline-offset:-1px !important;}',
    '#__ppx_bar{position:fixed;top:12px;right:12px;z-index:2147483647;width:300px;max-height:88vh;overflow:auto;',
    'background:#1f2329;color:#e6e6e6;font-size:12px;line-height:1.5;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.45);',
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif;padding:10px;}',
    '#__ppx_bar *{box-sizing:border-box;}',
    '#__ppx_bar h4{margin:0 0 8px;font-size:13px;color:#fff;display:flex;align-items:center;justify-content:space-between;}',
    '#__ppx_bar .__ppx_btns{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;}',
    '#__ppx_bar button{flex:1 1 46%;border:0;border-radius:6px;padding:6px 4px;cursor:pointer;font-size:12px;background:#2d333b;color:#cfd3da;}',
    '#__ppx_bar button:hover{background:#3a424d;}',
    '#__ppx_bar button.__ppx_on{background:#ff5722;color:#fff;}',
    '#__ppx_bar .__ppx_done{flex:1 1 100%;background:#2e7d32;color:#fff;font-weight:600;}',
    '#__ppx_bar .__ppx_done:hover{background:#388e3c;}',
    '#__ppx_bar .__ppx_sec{margin-top:6px;border-top:1px solid #333a44;padding-top:6px;}',
    '#__ppx_bar .__ppx_item{display:flex;align-items:flex-start;gap:6px;padding:3px 0;border-bottom:1px dashed #333a44;}',
    '#__ppx_bar .__ppx_item b{color:#ffcc80;}',
    '#__ppx_bar .__ppx_item .__ppx_s{flex:1;word-break:break-all;color:#9aa4b2;}',
    '#__ppx_bar .__ppx_del{flex:0 0 auto;color:#ef5350;cursor:pointer;font-weight:700;}',
    '#__ppx_bar .__ppx_tip{color:#7f8794;margin-top:6px;font-size:11px;}'
  ].join('\n');
  (document.head || document.documentElement).appendChild(style);

  // ----- 工具：判断 class 是否“稳定”（过滤动态/状态类） -----
  function isStableClass(c) {
    if (!c) return false;
    if (c.indexOf('__ppx') === 0) return false;
    // 过滤明显动态/哈希/状态类
    if (/^(active|hover|focus|selected|current|open|show|hidden|disabled|is-|js-|has-)/i.test(c)) return false;
    if (/\d{4,}/.test(c)) return false;          // 含长数字（多半是动态）
    if (/^[a-z0-9]{8,}$/i.test(c) && /[0-9]/.test(c) && /[a-z]/i.test(c)) return false; // 哈希样式
    if (c.length > 30) return false;
    return true;
  }

  function stableClasses(el) {
    if (!el.classList) return [];
    var out = [];
    el.classList.forEach(function (c) { if (isStableClass(c)) out.push(c); });
    return out;
  }

  // ----- 工具：生成单个元素相对于父级的“片段”选择器 -----
  function segFor(el) {
    var tag = el.tagName.toLowerCase();
    var cls = stableClasses(el);
    var seg = tag;
    if (cls.length) {
      seg += '.' + cls.slice(0, 2).map(function (c) { return CSS.escape(c); }).join('.');
    }
    // 若同级存在同样匹配 seg 的兄弟，则补 nth-of-type
    var parent = el.parentElement;
    if (parent) {
      var sameTag = Array.prototype.filter.call(parent.children, function (c) {
        return c.tagName === el.tagName;
      });
      if (sameTag.length > 1) {
        // 仅当 class 不能唯一定位时才加 nth-of-type
        var matchSeg = Array.prototype.filter.call(parent.children, function (c) {
          try { return c.matches(seg); } catch (e) { return false; }
        });
        if (matchSeg.length > 1) {
          var idx = sameTag.indexOf(el) + 1;
          seg += ':nth-of-type(' + idx + ')';
        }
      }
    }
    return seg;
  }

  // ----- 工具：生成绝对 CSS 选择器（优先 id） -----
  function cssPath(el, stopAt) {
    if (!el || el.nodeType !== 1) return '';
    if (el.id && /^[a-zA-Z][\w\-]*$/.test(el.id)) {
      return '#' + CSS.escape(el.id);
    }
    var parts = [];
    var cur = el;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement) {
      if (stopAt && cur === stopAt) break;
      if (cur.id && /^[a-zA-Z][\w\-]*$/.test(cur.id)) {
        parts.unshift('#' + CSS.escape(cur.id));
        return parts.join(' > ');
      }
      parts.unshift(segFor(cur));
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  }

  // ----- 工具：生成相对容器的选择器 -----
  function relativePath(el, container) {
    if (!container) return cssPath(el, null);
    var parts = [];
    var cur = el;
    while (cur && cur.nodeType === 1 && cur !== container) {
      parts.unshift(segFor(cur));
      cur = cur.parentElement;
    }
    if (cur !== container) {
      // el 不在容器内，退化为绝对路径
      return cssPath(el, null);
    }
    return parts.join(' > ');
  }

  // ----- 工具：向上寻找“与兄弟节点重复的最近祖先”作为列表块容器 -----
  function findRepeatingBlock(el) {
    var cur = el;
    var best = null;
    for (var depth = 0; cur && cur !== document.body && depth < 12; depth++, cur = cur.parentElement) {
      var parent = cur.parentElement;
      if (!parent) break;
      var seg = segFor(cur).replace(/:nth-of-type\(\d+\)/, ''); // 去掉 nth 以便匹配兄弟
      var matches;
      try {
        matches = parent.querySelectorAll(':scope > ' + seg);
      } catch (e) {
        matches = [];
      }
      if (matches && matches.length >= 2) {
        best = cur;
        // 找到第一个有重复兄弟的祖先即作为候选（最近的重复块）
        break;
      }
    }
    return best || el;
  }

  // ----- 工具：为容器生成选择器并统计匹配数 -----
  function buildContainerSelector(blockEl) {
    var parent = blockEl.parentElement;
    var seg = segFor(blockEl).replace(/:nth-of-type\(\d+\)/, '');
    var sel;
    var count = 0;
    // 优先尝试 “父绝对路径 > 子片段”
    if (parent) {
      var parentPath = cssPath(parent, null);
      sel = parentPath ? (parentPath + ' > ' + seg) : seg;
    } else {
      sel = seg;
    }
    try { count = document.querySelectorAll(sel).length; } catch (e) { count = 0; }
    if (count < 2) {
      // 退化为仅用片段全局匹配
      try {
        var c2 = document.querySelectorAll(seg).length;
        if (c2 >= 2) { sel = seg; count = c2; }
      } catch (e) {}
    }
    return { selector: sel, count: count };
  }

  // ----- 高亮匹配项 -----
  function clearMatches() {
    Array.prototype.forEach.call(document.querySelectorAll('.__ppx_match'), function (n) {
      n.classList.remove('__ppx_match');
    });
  }
  function highlightMatches(sel) {
    clearMatches();
    if (!sel) return 0;
    var n = 0;
    try {
      Array.prototype.forEach.call(document.querySelectorAll(sel), function (node) {
        node.classList.add('__ppx_match');
        n++;
      });
    } catch (e) {}
    return n;
  }

  // ----- 取样本文本/属性 -----
  function sampleOf(el, attr) {
    try {
      if (attr) return (el.getAttribute(attr) || '').trim().slice(0, 120);
      return (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120);
    } catch (e) { return ''; }
  }

  // ----- 自动判断字段属性 -----
  function autoAttr(el) {
    var tag = el.tagName.toLowerCase();
    if (tag === 'a') return 'href';
    if (tag === 'img') return 'src';
    return '';
  }

  // ----- 回调 Python -----
  function emit(payload) {
    try {
      if (window.__ppxEvent) {
        var r = window.__ppxEvent(payload);
        if (r && typeof r.then === 'function') { r.catch(function () {}); }
      }
    } catch (e) {}
  }

  // ----- 工具条 UI -----
  var bar = document.createElement('div');
  bar.id = '__ppx_bar';
  // 关键容器样式用 CSSOM 内联写死：el.style 走 CSSOM，不受目标站点 CSP style-src 限制，
  // 而上面注入的 <style> 标签在严格 CSP 站点可能被拦截，导致工具条丢失定位/背景而“看不见”。
  bar.style.cssText = [
    'position:fixed','top:12px','right:12px','z-index:2147483647','width:300px',
    'max-height:88vh','overflow:auto','background:#1f2329','color:#e6e6e6',
    'font-size:12px','line-height:1.5','border-radius:10px',
    'box-shadow:0 8px 30px rgba(0,0,0,.45)','padding:10px',
    'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Microsoft YaHei,sans-serif'
  ].join(';') + ';';

  // 确保工具条 / 样式始终挂在当前文档上：
  // 1) 注入脚本在 document-start 执行时 body 尚不存在，先挂 documentElement，
  //    待 body 就绪后由定时器自动迁移过去；
  // 2) SPA 框架渲染时可能整体替换 DOM 把工具条移除，检测到脱离后复用同一节点
  //    重新挂回（节点复用，render/事件闭包不失效）。
  function ensureBar() {
    try {
      if (!style.isConnected) (document.head || document.documentElement).appendChild(style);
      var host = document.body || document.documentElement;
      if (!bar.isConnected || bar.parentNode !== host) {
        host.appendChild(bar);
        plog('ensureBar: (re)mounted under ' + (host.tagName || '?'));
      }
    } catch (e) { plog('ensureBar error: ' + e); }
  }
  ensureBar();
  window.__ppxEnsureBar = ensureBar;
  setInterval(ensureBar, 1000);
  plog('bar created: styleConnected=' + style.isConnected + ' barConnected=' + bar.isConnected);
  // 延迟一拍报告工具条的真实可见性，便于判断是“没挂上”“被 CSP 去样式”还是“被遮挡”
  setTimeout(function () {
    try {
      ensureBar();
      var r = bar.getBoundingClientRect();
      var cs = getComputedStyle(bar);
      plog('visibility check: connected=' + bar.isConnected + ' parent=' + (bar.parentNode && bar.parentNode.tagName)
        + ' rect=' + Math.round(r.left) + ',' + Math.round(r.top) + ',' + Math.round(r.width) + 'x' + Math.round(r.height)
        + ' pos=' + cs.position + ' display=' + cs.display + ' visibility=' + cs.visibility
        + ' opacity=' + cs.opacity + ' zIndex=' + cs.zIndex);
    } catch (e) { plog('visibility check error: ' + e); }
  }, 800);

  var MODE_LABELS = {
    container: '①选列表块',
    field: '②选字段',
    pagination: '③选翻页按钮',
    detailField: '④选详情字段(可选)'
  };

  function render() {
    ensureBar();
    var html = '<h4>采集选取 <span style="font-weight:400;color:#9aa4b2;">点选模式</span></h4>';
    html += '<div class="__ppx_btns">';
    ['container', 'field', 'pagination', 'detailField'].forEach(function (m) {
      html += '<button data-mode="' + m + '" class="' + (state.mode === m ? '__ppx_on' : '') + '">' + MODE_LABELS[m] + '</button>';
    });
    html += '<button class="__ppx_done" data-act="done">✔ 完成选取</button>';
    html += '</div>';

    // 容器
    html += '<div class="__ppx_sec"><b>列表块：</b>' + (state.container ? '<span class="__ppx_s">' + escapeHtml(state.container) + '</span>' : '<span class="__ppx_tip">未选（整页当 1 条）</span>') + '</div>';

    // 字段
    html += '<div class="__ppx_sec"><b>字段(' + state.fields.length + ')</b>';
    state.fields.forEach(function (f) {
      html += '<div class="__ppx_item"><b>' + escapeHtml(f.name) + '</b><span class="__ppx_s">' + escapeHtml(f.sample || f.selector) + (f.attr ? ' @' + f.attr : '') + '</span><span class="__ppx_del" data-del="field" data-id="' + f.id + '">×</span></div>';
    });
    html += '</div>';

    // 翻页
    if (state.pagination) {
      html += '<div class="__ppx_sec"><b>翻页：</b><span class="__ppx_s">' + escapeHtml(state.pagination) + '</span></div>';
    }

    // 详情
    html += '<div class="__ppx_sec"><b>详情字段(' + state.detailFields.length + ')</b>';
    if (state.detailLinkField) {
      html += '<div class="__ppx_tip">入口字段：' + escapeHtml(state.detailLinkField) + '</div>';
    }
    state.detailFields.forEach(function (f) {
      html += '<div class="__ppx_item"><b>' + escapeHtml(f.name) + '</b><span class="__ppx_s">' + escapeHtml(f.sample || f.selector) + (f.attr ? ' @' + f.attr : '') + '</span><span class="__ppx_del" data-del="detail" data-id="' + f.id + '">×</span></div>';
    });
    html += '</div>';

    html += '<div class="__ppx_tip">提示：先选「列表块」，再选「字段」。在字段模式点击链接会自动记录为详情入口。</div>';
    bar.innerHTML = html;
  }
  window.__ppxRenderToolbar = render;

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // ----- 工具条点击处理 -----
  bar.addEventListener('click', function (ev) {
    var t = ev.target;
    ev.stopPropagation();
    if (t.dataset && t.dataset.mode) {
      state.mode = t.dataset.mode;
      render();
      return;
    }
    if (t.dataset && t.dataset.act === 'done') {
      emit({ type: 'done' });
      var tip = document.createElement('div');
      tip.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#2e7d32;color:#fff;text-align:center;padding:8px;z-index:2147483647;font-size:14px;';
      tip.textContent = '已记录选择，请勿关闭此窗口；回到 PPX 点「开始采集」即可在本页采集';
      document.documentElement.appendChild(tip);
      setTimeout(function () { try { tip.remove(); } catch (e) {} }, 4000);
      return;
    }
    if (t.dataset && t.dataset.del) {
      var id = parseInt(t.dataset.id, 10);
      if (t.dataset.del === 'field') {
        state.fields = state.fields.filter(function (f) { return f.id !== id; });
      } else {
        state.detailFields = state.detailFields.filter(function (f) { return f.id !== id; });
      }
      emit({ type: 'sync', state: snapshot() });
      render();
      return;
    }
  }, true);

  function snapshot() {
    return {
      container: state.container,
      fields: state.fields,
      pagination: state.pagination,
      detailFields: state.detailFields,
      detailLinkField: state.detailLinkField
    };
  }

  // ----- 悬停高亮 -----
  var lastHover = null;
  document.addEventListener('mouseover', function (ev) {
    var t = ev.target;
    if (!t || t.closest && t.closest('#__ppx_bar')) return;
    if (lastHover && lastHover !== t) lastHover.classList.remove('__ppx_hover');
    lastHover = t;
    t.classList.add('__ppx_hover');
  }, true);
  document.addEventListener('mouseout', function (ev) {
    var t = ev.target;
    if (t && t.classList) t.classList.remove('__ppx_hover');
  }, true);

  // ----- 点击拾取 -----
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t) return;
    if (t.closest && t.closest('#__ppx_bar')) return; // 工具条自身不拦截
    ev.preventDefault();
    ev.stopPropagation();
    ev.stopImmediatePropagation();

    if (state.mode === 'container') {
      var block = findRepeatingBlock(t);
      var built = buildContainerSelector(block);
      state.container = built.selector;
      var n = highlightMatches(built.selector);
      emit({ type: 'container', selector: built.selector, sample: sampleOf(block, ''), count: n });
      render();
    } else if (state.mode === 'field') {
      var attr = autoAttr(t);
      var containerEl = state.container ? (function () {
        try { return t.closest(state.container); } catch (e) { return null; }
      })() : null;
      var sel = containerEl ? relativePath(t, containerEl) : cssPath(t, null);
      // 在字段模式点击链接 → 记录详情入口字段名
      var name = 'field' + (state.fields.length + 1);
      var fid = ++seq;
      var item = { id: fid, name: name, selector: sel, attr: attr, sample: sampleOf(t, attr) };
      state.fields.push(item);
      if (t.tagName.toLowerCase() === 'a' && !state.detailLinkField) {
        state.detailLinkField = name;
      }
      emit({ type: 'field', id: fid, name: name, selector: sel, attr: attr, sample: item.sample, isLink: t.tagName.toLowerCase() === 'a' });
      render();
    } else if (state.mode === 'pagination') {
      var psel = cssPath(t, null);
      state.pagination = psel;
      emit({ type: 'pagination', selector: psel, sample: sampleOf(t, '') });
      render();
    } else if (state.mode === 'detailField') {
      var dattr = autoAttr(t);
      var dsel = cssPath(t, null);
      var dname = 'detail' + (state.detailFields.length + 1);
      var did = ++seq;
      var ditem = { id: did, name: dname, selector: dsel, attr: dattr, sample: sampleOf(t, dattr) };
      state.detailFields.push(ditem);
      emit({ type: 'detailField', id: did, name: dname, selector: dsel, attr: dattr, sample: ditem.sample });
      render();
    }
  }, true);

  render();
  } // end install()

  boot();
})();
"""


# 浏览器反自动化检测（best-effort）：降低被 Cloudflare 等基础人机校验拦截的概率。
# 注意：对开启了「Managed Challenge / 强校验」的站点（如 linux.do）不保证有效，
# 那类站点通常还需配合真实指纹/住宅代理等更重的手段。
_WA_LAUNCH_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-features=AutomationControlled',
]
# 统一一个真实的桌面 Chrome UA（Playwright 1.48 内核为 Chromium 130），
# 同时避免无头模式 UA 里出现 HeadlessChrome 这一明显特征。
_WA_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
)
# 注入到页面最前面的反检测脚本（抹掉常见自动化特征）。
_STEALTH_INIT = r"""
(() => {
  try { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); } catch (e) {}
  try { window.chrome = window.chrome || { runtime: {} }; } catch (e) {}
  try { Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] }); } catch (e) {}
  try { Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] }); } catch (e) {}
  try {
    var q = navigator.permissions && navigator.permissions.query;
    if (q) {
      navigator.permissions.query = function (p) {
        return (p && p.name === 'notifications')
          ? Promise.resolve({ state: Notification.permission })
          : q(p);
      };
    }
  } catch (e) {}
})();
"""


class WebAutoTool:
    """网页自动化采集工具"""

    # 共享状态延迟初始化（避免与多重继承的 __init__ 冲突）
    _wa_lock: Optional[threading.Lock] = None

    # ------------------------------------------------------------------ #
    # 浏览器内核下载源（国内 / 海外多地址，避免单一地址下载失败）
    # host 为空表示使用 playwright 内置默认 CDN；非空时通过
    # PLAYWRIGHT_DOWNLOAD_HOST 覆盖，下载路径仍为 builds/chromium/<rev>/...
    # ------------------------------------------------------------------ #
    _WA_DOWNLOAD_SOURCES: List[Dict[str, str]] = [
        {
            'id': 'npmmirror',
            'name': '国内镜像 · npmmirror（淘宝，推荐国内用户）',
            'host': 'https://cdn.npmmirror.com/binaries/playwright',
            'region': 'cn',
        },
        {
            'id': 'default',
            'name': '官方默认（海外节点，自动选择）',
            'host': '',
            'region': 'global',
        },
        {
            'id': 'azure',
            'name': '海外官方 · Azure CDN',
            'host': 'https://playwright.azureedge.net',
            'region': 'global',
        },
        {
            'id': 'akamai',
            'name': '海外官方 · Akamai 节点',
            'host': 'https://playwright-akamai.azureedge.net',
            'region': 'global',
        },
        {
            'id': 'verizon',
            'name': '海外官方 · Verizon 节点',
            'host': 'https://playwright-verizon.azureedge.net',
            'region': 'global',
        },
    ]

    # ------------------------------------------------------------------ #
    # 内部：共享状态初始化与访问
    # ------------------------------------------------------------------ #
    def _wa_ensure(self) -> None:
        """惰性初始化共享状态（线程锁、状态字典）。"""
        if getattr(self, '_wa_lock', None) is not None:
            return
        self._wa_lock = threading.Lock()
        # 点选会话状态
        self._wa_pick: Dict[str, Any] = self._wa_blank_pick()
        self._wa_pick_thread: Optional[threading.Thread] = None
        self._wa_pick_stop = threading.Event()
        # 采集任务状态
        self._wa_run: Dict[str, Any] = self._wa_blank_run()
        self._wa_run_thread: Optional[threading.Thread] = None
        self._wa_run_stop = threading.Event()
        # 同一浏览器会话内的采集请求（None=空闲）：由前端置入，点选线程取走执行，
        # 从而复用用户已通过 CF/登录的会话，彻底规避反爬检测。
        self._wa_collect_req: Optional[Dict[str, Any]] = None
        # 浏览器内核下载状态
        self._wa_install: Dict[str, Any] = {
            'installing': False, 'done': False, 'success': False,
            'progress': -1, 'error': '', 'host': '',
        }
        self._wa_install_thread: Optional[threading.Thread] = None

    @staticmethod
    def _wa_blank_pick() -> Dict[str, Any]:
        return {
            'active': False, 'url': '', 'mode': 'container',
            'container': '', 'containerSample': '',
            'fields': [], 'pagination': '',
            'detailActive': False, 'detailFields': [], 'detailLinkField': '',
            'done': False, 'error': '',
        }

    @staticmethod
    def _wa_blank_run() -> Dict[str, Any]:
        return {
            'running': False, 'done': False, 'success': False,
            'page': 0, 'total': 0, 'columns': [], 'rows': [],
            'outputPath': '', 'error': '',
        }

    # ------------------------------------------------------------------ #
    # 内部：playwright 可用性 / 内核检测
    # ------------------------------------------------------------------ #
    @staticmethod
    def _wa_playwright_ready() -> bool:
        """playwright python 包是否可导入。"""
        try:
            import importlib.util
            return importlib.util.find_spec('playwright') is not None
        except Exception:
            return False

    @staticmethod
    def _wa_browsers_dir() -> Path:
        """playwright 浏览器缓存目录。"""
        env = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
        if env:
            return Path(env)
        if sys.platform.startswith('win'):
            base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
            return Path(base) / 'ms-playwright'
        if sys.platform == 'darwin':
            return Path.home() / 'Library' / 'Caches' / 'ms-playwright'
        return Path.home() / '.cache' / 'ms-playwright'

    @staticmethod
    def _wa_expected_chromium_dirs() -> List[str]:
        """读取当前 playwright 包要求的 chromium 内核目录名（含修订号）。

        从 playwright 自带的 browsers.json 解析期望修订号，确保检测到的内核
        与已安装的 playwright 版本严格匹配；否则残留的旧/新修订号内核会被误判
        为「已就绪」，导致实际 launch 时报「请运行 playwright install」版本不符。
        返回空列表表示无法确定（调用方回退到宽松匹配）。
        """
        try:
            import importlib.util
            spec = importlib.util.find_spec('playwright')
            if not spec or not spec.origin:
                return []
            json_path = Path(spec.origin).parent / 'driver' / 'package' / 'browsers.json'
            data = json.loads(json_path.read_text(encoding='utf-8'))
        except Exception:
            return []
        dirs: List[str] = []
        for browser in data.get('browsers', []):
            name = browser.get('name', '')
            revision = browser.get('revision')
            # 仅关注默认安装的 chromium 主内核（排除 tip-of-tree 等非默认项）
            if (not revision or not name.startswith('chromium')
                    or name == 'chromium-tip-of-tree'
                    or not browser.get('installByDefault', False)):
                continue
            dirs.append(f"{name.replace('-', '_')}-{revision}")
        return dirs

    @classmethod
    def _wa_chromium_installed(cls) -> bool:
        """检测与当前 playwright 版本匹配的 chromium 内核是否已下载。"""
        base = cls._wa_browsers_dir()
        if not base.exists():
            return False
        expected = cls._wa_expected_chromium_dirs()
        if expected:
            # 严格校验：必须存在与当前 playwright 版本匹配的内核目录，
            # 避免残留的不匹配修订号被误判为已就绪。
            return all((base / dirname).exists() for dirname in expected)
        # 回退：无法读取期望修订号时，宽松匹配任意 chromium 目录
        patterns = [str(base / 'chromium-*'), str(base / 'chromium_headless_shell-*')]
        return any(glob.glob(pattern) for pattern in patterns)

    # ------------------------------------------------------------------ #
    # 1. 状态查询
    # ------------------------------------------------------------------ #
    def webauto_status(self):
        """返回 playwright/内核就绪状态及当前是否有点选/采集进行中。"""
        try:
            self._wa_ensure()
            ready = self._wa_playwright_ready()
            installed = self._wa_chromium_installed() if ready else False
            with self._wa_lock:
                picking = bool(self._wa_pick.get('active'))
                running = bool(self._wa_run.get('running'))
            return api_success(
                installed=installed, ready=ready,
                picking=picking, running=running,
            )
        except Exception as exc:
            return api_error(f'获取状态失败：{exc}')

    # ------------------------------------------------------------------ #
    # 2. 浏览器内核下载源 / 安装
    # ------------------------------------------------------------------ #
    def webauto_download_sources(self):
        """返回可选的浏览器内核下载源（国内 / 海外多地址）。

        前端据此渲染「下载来源」下拉，并把所选 source / host 回传给
        webauto_install_browser，避免单一地址下载失败。
        """
        try:
            return api_success(sources=[dict(s) for s in self._WA_DOWNLOAD_SOURCES])
        except Exception as exc:
            return api_error(f'获取下载源失败：{exc}')

    @classmethod
    def _wa_resolve_source_host(cls, source_id: str) -> str:
        """按预设下载源 id 解析对应的 host。"""
        for s in cls._WA_DOWNLOAD_SOURCES:
            if s['id'] == source_id:
                return s['host']
        return ''

    @classmethod
    def _wa_resolve_download_host(cls, options: Dict | None) -> str:
        """从前端 options 解析最终下载地址（PLAYWRIGHT_DOWNLOAD_HOST）。

        优先级：显式 host > 预设 source id。空字符串表示用官方默认 CDN。
        """
        options = options or {}
        host = str(options.get('host') or '').strip()
        if not host:
            src_id = str(options.get('source') or '').strip()
            if src_id and src_id != 'custom':
                host = cls._wa_resolve_source_host(src_id)
        host = host.strip().rstrip('/')
        if host and not re.match(r'^https?://', host, re.I):
            host = 'https://' + host
        return host

    def webauto_install_browser(self, options: Dict | None = None):
        """启动后台线程下载 chromium 内核。

        options 可选：
          - host:   直接指定下载地址（优先级最高，支持自定义镜像）
          - source: 预设下载源 id（见 webauto_download_sources）
        """
        try:
            self._wa_ensure()
            if not self._wa_playwright_ready():
                return api_error('未检测到 playwright 依赖，请先运行 pnpm run init 安装环境')
            if self._wa_chromium_installed():
                return api_success('浏览器内核已就绪', installed=True)
            host = self._wa_resolve_download_host(options)
            with self._wa_lock:
                if self._wa_install['installing']:
                    return api_success('已开始下载浏览器内核')
                self._wa_install = {
                    'installing': True, 'done': False, 'success': False,
                    'progress': 0, 'error': '', 'host': host,
                }
            self._wa_install_thread = threading.Thread(
                target=self._wa_install_worker, args=(host,), daemon=True,
            )
            self._wa_install_thread.start()
            return api_success('已开始下载浏览器内核')
        except Exception as exc:
            return api_error(f'启动下载失败：{exc}')

    def _wa_install_worker(self, host: str = '') -> None:
        """后台线程：执行 playwright install chromium，实时解析进度。

        host 非空时通过 PLAYWRIGHT_DOWNLOAD_HOST 指定下载源（国内 / 海外镜像）。
        """
        try:
            env = {**os.environ}
            if host:
                env['PLAYWRIGHT_DOWNLOAD_HOST'] = host
            # 放宽下载连接超时，弱网环境下减少因超时导致的失败
            env.setdefault('PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT', '120000')
            proc = subprocess.Popen(
                [sys.executable, '-m', 'playwright', 'install', 'chromium'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace',
                env=env,
            )
            pct_re = re.compile(r'(\d{1,3})\s*%')
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                low = line.lower()
                progress = -1
                match = pct_re.search(line)
                if match:
                    try:
                        progress = max(0, min(100, int(match.group(1))))
                    except Exception:
                        progress = -1
                elif 'download' in low:
                    progress = 10
                elif 'extract' in low or 'unzip' in low:
                    progress = 80
                with self._wa_lock:
                    if progress >= 0:
                        self._wa_install['progress'] = progress
            proc.wait()
            success = proc.returncode == 0 and self._wa_chromium_installed()
            with self._wa_lock:
                self._wa_install['installing'] = False
                self._wa_install['done'] = True
                self._wa_install['success'] = success
                self._wa_install['progress'] = 100 if success else self._wa_install['progress']
                if not success:
                    self._wa_install['error'] = '内核下载失败，可切换其他下载来源后重试'
        except Exception as exc:
            with self._wa_lock:
                self._wa_install['installing'] = False
                self._wa_install['done'] = True
                self._wa_install['success'] = False
                self._wa_install['error'] = f'下载异常：{exc}'

    # ------------------------------------------------------------------ #
    # 3. 安装进度
    # ------------------------------------------------------------------ #
    def webauto_install_status(self):
        """轮询内核下载进度。"""
        try:
            self._wa_ensure()
            with self._wa_lock:
                st = dict(self._wa_install)
            return api_success(
                installing=bool(st['installing']),
                done=bool(st['done']),
                success=bool(st['success']),
                progress=int(st['progress']),
                error=st['error'],
            )
        except Exception as exc:
            return api_error(f'获取下载进度失败：{exc}')

    # ------------------------------------------------------------------ #
    # 4. 启动点选
    # ------------------------------------------------------------------ #
    def webauto_pick_start(self, options: Dict | None = None):
        """启动可视化点选会话（后台线程开有头浏览器并注入点选脚本）。"""
        try:
            self._wa_ensure()
            options = options or {}
            url = str(options.get('url') or '').strip()
            if not url:
                return api_error('请输入要采集的网页地址')
            if not re.match(r'^https?://', url, re.I):
                url = 'http://' + url
            if not self._wa_playwright_ready():
                return api_error('未检测到 playwright 依赖，请先运行 pnpm run init 安装环境')
            if not self._wa_chromium_installed():
                return api_error('浏览器内核尚未安装，请先点击「下载浏览器内核」')
            with self._wa_lock:
                if self._wa_pick.get('active'):
                    return api_error('已有一个点选会话在进行中，请先取消或完成')
                if self._wa_run.get('running'):
                    return api_error('正在采集中，无法同时点选')
                self._wa_pick = self._wa_blank_pick()
                self._wa_pick['active'] = True
                self._wa_pick['url'] = url
            self._wa_pick_stop.clear()
            self._wa_pick_thread = threading.Thread(
                target=self._wa_pick_worker, args=(url,), daemon=True,
            )
            self._wa_pick_thread.start()
            return api_success('点选已启动')
        except Exception as exc:
            return api_error(f'启动点选失败：{exc}')

    def _wa_pick_worker(self, url: str) -> None:
        """后台线程：完整的点选会话生命周期（线程亲和的 playwright 全在此线程内）。"""
        playwright = browser = page = None
        try:
            from playwright.sync_api import sync_playwright

            def on_event(source, payload):
                """页面 JS 通过 window.__ppxEvent 回调进入这里（带锁更新状态）。"""
                try:
                    self._wa_handle_pick_event(payload)
                except Exception:
                    pass
                return True

            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=False, args=_WA_LAUNCH_ARGS)
            context = browser.new_context(locale='zh-CN', user_agent=_WA_USER_AGENT)
            context.add_init_script(_STEALTH_INIT)
            page = context.new_page()

            # 诊断：把浏览器控制台 [PPXBAR] 日志与页面 JS 错误转发到后端终端，
            # 便于排查工具条不显示的问题（只透传我们自己的日志与 error，避免刷屏）。
            def _on_console(msg):
                try:
                    text = msg.text
                    mtype = msg.type
                except Exception:
                    text, mtype = str(msg), ''
                if 'PPXBAR' in text or mtype == 'error':
                    print(f'[webauto:console:{mtype}] {text}', flush=True)

            page.on('console', _on_console)
            page.on('pageerror', lambda err: print(f'[webauto:pageerror] {err}', flush=True))

            # 暴露回调 + 注入脚本（init_script 保证后续导航也注入）
            page.expose_binding('__ppxEvent', on_event)
            page.add_init_script(_PICK_SCRIPT)

            def reinject(_frame=None):
                try:
                    page.evaluate(_PICK_SCRIPT)
                except Exception as exc:
                    print(f'[webauto:reinject-error] {exc}', flush=True)

            page.on('framenavigated', reinject)

            try:
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
            except Exception:
                # 加载超时也继续，让用户能在已渲染的部分上点选
                pass
            reinject()

            # 主循环：在【同一浏览器/同一会话】里待命，处理采集请求，直到用户关闭会话或手动关窗。
            # 注意：点选「完成」(done) 不再关闭浏览器——保持打开以便在已通过 CF/登录的会话内直接采集。
            while not self._wa_pick_stop.is_set():
                # 1) 取采集请求并就地执行（线程亲和：采集与点选共用同一线程/页面）
                req = None
                with self._wa_lock:
                    if self._wa_collect_req is not None:
                        req = self._wa_collect_req
                        self._wa_collect_req = None
                if req is not None:
                    self._wa_collect_in_session(page, context, req)
                    continue
                # 2) 检测窗口是否被用户手动关闭
                try:
                    if page.is_closed():
                        with self._wa_lock:
                            self._wa_pick['done'] = True
                        break
                except Exception:
                    with self._wa_lock:
                        self._wa_pick['done'] = True
                    break
                time.sleep(0.2)
        except Exception as exc:
            with self._wa_lock:
                self._wa_pick['error'] = f'点选会话异常：{exc}'
                self._wa_pick['done'] = True
        finally:
            # 在本线程内关闭，保证线程亲和
            try:
                if browser is not None:
                    browser.close()
            except Exception:
                pass
            try:
                if playwright is not None:
                    playwright.stop()
            except Exception:
                pass
            with self._wa_lock:
                self._wa_pick['active'] = False

    def _wa_handle_pick_event(self, payload: Dict[str, Any]) -> None:
        """处理来自页面的点选事件，更新加锁的共享状态。"""
        if not isinstance(payload, dict):
            return
        etype = payload.get('type')
        with self._wa_lock:
            if etype == 'container':
                self._wa_pick['container'] = payload.get('selector', '')
                self._wa_pick['containerSample'] = payload.get('sample', '')
                self._wa_pick['mode'] = 'container'
            elif etype == 'field':
                self._wa_pick['fields'].append({
                    'id': str(payload.get('id', '')),
                    'name': payload.get('name', ''),
                    'selector': payload.get('selector', ''),
                    'attr': payload.get('attr', ''),
                    'sample': payload.get('sample', ''),
                })
                # 记录详情入口字段（首次点击链接进入详情）
                if payload.get('isLink') and not self._wa_pick['detailLinkField']:
                    self._wa_pick['detailLinkField'] = payload.get('name', '')
                self._wa_pick['mode'] = 'field'
            elif etype == 'pagination':
                self._wa_pick['pagination'] = payload.get('selector', '')
                self._wa_pick['mode'] = 'pagination'
            elif etype == 'detailField':
                self._wa_pick['detailActive'] = True
                self._wa_pick['detailFields'].append({
                    'id': str(payload.get('id', '')),
                    'name': payload.get('name', ''),
                    'selector': payload.get('selector', ''),
                    'attr': payload.get('attr', ''),
                    'sample': payload.get('sample', ''),
                })
                self._wa_pick['mode'] = 'detailField'
            elif etype == 'done':
                self._wa_pick['done'] = True
            elif etype == 'sync':
                # 页面侧删除项后整体同步
                st = payload.get('state') or {}
                if 'container' in st:
                    self._wa_pick['container'] = st.get('container', '')
                if 'pagination' in st:
                    self._wa_pick['pagination'] = st.get('pagination', '')
                if 'detailLinkField' in st:
                    self._wa_pick['detailLinkField'] = st.get('detailLinkField', '')
                if isinstance(st.get('fields'), list):
                    self._wa_pick['fields'] = [{
                        'id': str(f.get('id', '')),
                        'name': f.get('name', ''),
                        'selector': f.get('selector', ''),
                        'attr': f.get('attr', ''),
                        'sample': f.get('sample', ''),
                    } for f in st['fields']]
                if isinstance(st.get('detailFields'), list):
                    self._wa_pick['detailFields'] = [{
                        'id': str(f.get('id', '')),
                        'name': f.get('name', ''),
                        'selector': f.get('selector', ''),
                        'attr': f.get('attr', ''),
                        'sample': f.get('sample', ''),
                    } for f in st['detailFields']]

    # ------------------------------------------------------------------ #
    # 5. 点选状态（前端高频轮询）
    # ------------------------------------------------------------------ #
    def webauto_pick_state(self):
        """返回当前点选会话的实时状态。"""
        try:
            self._wa_ensure()
            with self._wa_lock:
                st = self._wa_pick
                return api_success(
                    active=bool(st['active']),
                    url=st['url'],
                    mode=st['mode'],
                    container=st['container'],
                    containerSample=st['containerSample'],
                    fields=[dict(f) for f in st['fields']],
                    pagination=st['pagination'],
                    detailActive=bool(st['detailActive']),
                    detailFields=[dict(f) for f in st['detailFields']],
                    done=bool(st['done']),
                    error=st['error'],
                )
        except Exception as exc:
            return api_error(f'获取点选状态失败：{exc}')

    # ------------------------------------------------------------------ #
    # 6. 关闭会话（取消点选 / 结束整个任务，关闭浏览器）
    # ------------------------------------------------------------------ #
    def webauto_pick_cancel(self):
        """关闭浏览器会话、停止采集、清空状态。"""
        try:
            self._wa_ensure()
            # 同时停止可能正在进行的会话内采集
            self._wa_run_stop.set()
            self._wa_pick_stop.set()
            thread = self._wa_pick_thread
            if thread is not None:
                thread.join(timeout=8)
            with self._wa_lock:
                self._wa_pick = self._wa_blank_pick()
                self._wa_collect_req = None
            return api_success('已关闭浏览器')
        except Exception as exc:
            return api_error(f'关闭失败：{exc}')

    # webauto_session_close 是 webauto_pick_cancel 的语义别名（结束整个任务）
    def webauto_session_close(self):
        """结束整个采集任务并关闭浏览器（与取消点选同义）。"""
        return self.webauto_pick_cancel()

    # ------------------------------------------------------------------ #
    # 7. 完成点选（不关闭浏览器：保持会话以便在同一浏览器内采集）
    # ------------------------------------------------------------------ #
    def webauto_pick_finish(self):
        """标记点选阶段完成并返回当前配置快照；浏览器保持打开以便就地采集。"""
        try:
            self._wa_ensure()
            with self._wa_lock:
                st = self._wa_pick
                st['done'] = True
                config = {
                    'url': st['url'],
                    'container': st['container'],
                    'fields': [
                        {'id': f['id'], 'name': f['name'], 'selector': f['selector'], 'attr': f['attr']}
                        for f in st['fields']
                    ],
                    'pagination': st['pagination'],
                    'detailEnabled': bool(st['detailFields']),
                    'detailLinkField': st['detailLinkField'],
                    'detailFields': [
                        {'id': f['id'], 'name': f['name'], 'selector': f['selector'], 'attr': f['attr']}
                        for f in st['detailFields']
                    ],
                }
            return api_success('已完成选取', config=config)
        except Exception as exc:
            return api_error(f'完成选取失败：{exc}')

    # ------------------------------------------------------------------ #
    # 8. 启动采集（在点选用的同一浏览器/同一会话内执行，复用已通过 CF/登录的页面）
    # ------------------------------------------------------------------ #
    def webauto_collect_start(self, options: Dict | None = None):
        """在当前点选会话的浏览器里就地采集。

        选择器（container / 各字段 / 翻页 / 详情字段）一律取自服务端点选状态，
        前端只需传可编辑项：字段名 / 类型、翻页与详情开关、条数上限、导出格式。
        """
        try:
            self._wa_ensure()
            options = options or {}
            with self._wa_lock:
                if not self._wa_pick.get('active'):
                    return api_error('浏览器会话未打开，请先点击「打开浏览器开始点选」')
                if self._wa_run.get('running'):
                    return api_error('已有采集任务在进行中')
                if self._wa_collect_req is not None:
                    return api_error('采集正在排队启动，请稍候')
                config = self._wa_build_collect_config(options)
                if not config['fields']:
                    return api_error('请先在浏览器里点选至少一个字段')
                self._wa_run = self._wa_blank_run()
                self._wa_run['running'] = True
                self._wa_run['columns'] = self._wa_compute_columns(config)
                # 交给点选线程执行（线程亲和）
                self._wa_run_stop.clear()
                self._wa_collect_req = config
            return api_success('采集已开始')
        except Exception as exc:
            return api_error(f'启动采集失败：{exc}')

    def _wa_build_collect_config(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """合并：服务端点选状态里的选择器 + 前端传入的可编辑项，组装采集配置。

        必须在持有 self._wa_lock 的上下文中调用（读取 self._wa_pick）。
        """
        st = self._wa_pick
        # 字段名/类型覆盖：按 id 对应（前端 options.fields=[{id,name,attr}]）
        name_by_id = {}
        attr_by_id = {}
        for f in (options.get('fields') or []):
            fid = str(f.get('id', ''))
            if fid:
                name_by_id[fid] = f.get('name', '')
                attr_by_id[fid] = f.get('attr', '')
        fields = []
        for f in st['fields']:
            fid = str(f.get('id', ''))
            fields.append({
                'name': name_by_id.get(fid) or f.get('name', ''),
                'selector': f.get('selector', ''),
                'attr': attr_by_id.get(fid, f.get('attr', '')),
            })
        detail_fields = [
            {'name': f.get('name', ''), 'selector': f.get('selector', ''), 'attr': f.get('attr', '')}
            for f in st['detailFields']
        ]
        pg_opt = options.get('pagination') or {}
        detail_opt = options.get('detail') or {}
        return {
            'container': st['container'],
            'fields': fields,
            'pagination': {
                'enabled': bool(pg_opt.get('enabled')) and bool(st['pagination']),
                'selector': st['pagination'],
                'maxPages': int(pg_opt.get('maxPages') or 1),
                'waitMs': int(pg_opt.get('waitMs') or 1000),
            },
            'detail': {
                'enabled': bool(detail_opt.get('enabled')) and bool(detail_fields),
                'linkField': detail_opt.get('linkField') or st['detailLinkField'],
                'fields': detail_fields,
            },
            'limit': int(options.get('limit') or 0),
            'export': options.get('export') or {},
        }

    def _wa_collect_in_session(self, page, context, config: Dict[str, Any]) -> None:
        """在当前会话页面上执行采集（不开浏览器、不导航、不关闭）。结果写入 self._wa_run。

        天然复用用户已在该浏览器中通过 CF / 登录 / 导航后的页面，彻底规避反爬。
        """
        rows: List[Dict[str, Any]] = []
        columns = self._wa_compute_columns(config)
        with self._wa_lock:
            self._wa_run['columns'] = list(columns)
        try:
            container = (config.get('container') or '').strip()
            fields = config.get('fields') or []
            pagination = config.get('pagination') or {}
            detail = config.get('detail') or {}
            limit = int(config.get('limit') or 0)
            export = config.get('export') or {}

            pg_enabled = bool(pagination.get('enabled'))
            pg_selector = (pagination.get('selector') or '').strip()
            pg_max = int(pagination.get('maxPages') or 1)
            pg_wait = int(pagination.get('waitMs') or 1000)

            detail_enabled = bool(detail.get('enabled'))
            detail_link_field = detail.get('linkField') or ''
            detail_fields = detail.get('fields') or []

            current_page = 0
            while not self._wa_run_stop.is_set():
                current_page += 1
                with self._wa_lock:
                    self._wa_run['page'] = current_page
                try:
                    page.wait_for_timeout(300)
                except Exception:
                    pass

                # 抓取当前页的所有列表块
                blocks = []
                if container:
                    try:
                        blocks = page.query_selector_all(container)
                    except Exception:
                        blocks = []
                if not blocks:
                    # 无容器或匹配不到 → 整页当作 1 条
                    blocks = [page]

                for block in blocks:
                    if self._wa_run_stop.is_set():
                        break
                    if limit and len(rows) >= limit:
                        break
                    record = self._wa_extract_block(block, fields)

                    # 详情页采集
                    if detail_enabled and detail_link_field and block is not page:
                        href = self._wa_block_link(block, fields, detail_link_field)
                        if href:
                            detail_url = self._wa_abs_url(page.url, href)
                            self._wa_scrape_detail(context, detail_url, detail_fields, record)

                    rows.append(record)
                    with self._wa_lock:
                        self._wa_run['total'] = len(rows)
                        self._wa_run['rows'] = [dict(r) for r in rows[:50]]

                if limit and len(rows) >= limit:
                    break

                # 翻页
                if not pg_enabled or current_page >= pg_max:
                    break
                if not pg_selector:
                    break
                try:
                    nxt = page.query_selector(pg_selector)
                    if not nxt:
                        break
                    nxt.click()
                    page.wait_for_timeout(max(0, pg_wait))
                except Exception:
                    break

            # 导出
            output_path = ''
            try:
                output_path = self._wa_export(rows, columns, export)
            except Exception as exc:
                with self._wa_lock:
                    self._wa_run['error'] = f'导出失败：{exc}'

            with self._wa_lock:
                self._wa_run['running'] = False
                self._wa_run['done'] = True
                self._wa_run['success'] = True
                self._wa_run['total'] = len(rows)
                self._wa_run['rows'] = [dict(r) for r in rows[:50]]
                self._wa_run['outputPath'] = output_path
        except Exception as exc:
            with self._wa_lock:
                self._wa_run['running'] = False
                self._wa_run['done'] = True
                self._wa_run['success'] = False
                self._wa_run['error'] = f'采集异常：{exc}'

    # ------------------------------------------------------------------ #
    # 采集辅助方法
    # ------------------------------------------------------------------ #
    @staticmethod
    def _wa_compute_columns(config: Dict[str, Any]) -> List[str]:
        """计算导出列（列表字段 + 详情字段）。"""
        cols: List[str] = []
        for f in (config.get('fields') or []):
            name = f.get('name')
            if name and name not in cols:
                cols.append(name)
        detail = config.get('detail') or {}
        if detail.get('enabled'):
            for f in (detail.get('fields') or []):
                name = f.get('name')
                if name and name not in cols:
                    cols.append(name)
        return cols

    @staticmethod
    def _wa_extract_block(block, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按字段相对选择器从单个块中取值；单字段失败跳过。"""
        record: Dict[str, Any] = {}
        for field in fields:
            name = field.get('name') or ''
            selector = field.get('selector') or ''
            attr = field.get('attr') or ''
            value = ''
            try:
                if not selector:
                    target = block
                else:
                    target = block.query_selector(selector)
                if target is not None:
                    if attr:
                        value = target.get_attribute(attr) or ''
                    else:
                        value = (target.inner_text() or '').strip()
            except Exception:
                value = ''
            record[name] = value
        return record

    @staticmethod
    def _wa_block_link(block, fields: List[Dict[str, Any]], link_field: str) -> str:
        """取指定字段在块内对应链接的 href。"""
        field = next((f for f in fields if f.get('name') == link_field), None)
        if not field:
            return ''
        selector = field.get('selector') or ''
        try:
            target = block.query_selector(selector) if selector else block
            if target is None:
                return ''
            href = target.get_attribute('href')
            if href:
                return href
            # 若该字段不是链接本身，尝试取其内部 a
            inner = target.query_selector('a')
            if inner is not None:
                return inner.get_attribute('href') or ''
        except Exception:
            return ''
        return ''

    @staticmethod
    def _wa_abs_url(base: str, href: str) -> str:
        """相对链接转绝对链接。"""
        try:
            from urllib.parse import urljoin
            return urljoin(base, href)
        except Exception:
            return href

    def _wa_scrape_detail(self, context, detail_url: str, detail_fields: List[Dict[str, Any]],
                          record: Dict[str, Any]) -> None:
        """在新标签页打开详情链接，抓取详情字段后合并进 record。"""
        if not detail_url:
            return
        tab = None
        try:
            tab = context.new_page()
            tab.goto(detail_url, wait_until='domcontentloaded', timeout=60000)
            try:
                tab.wait_for_timeout(300)
            except Exception:
                pass
            for field in detail_fields:
                name = field.get('name') or ''
                selector = field.get('selector') or ''
                attr = field.get('attr') or ''
                value = ''
                try:
                    target = tab.query_selector(selector) if selector else None
                    if target is not None:
                        if attr:
                            value = target.get_attribute(attr) or ''
                        else:
                            value = (target.inner_text() or '').strip()
                except Exception:
                    value = ''
                record[name] = value
        except Exception:
            pass
        finally:
            try:
                if tab is not None:
                    tab.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # 导出
    # ------------------------------------------------------------------ #
    @staticmethod
    def _wa_export(rows: List[Dict[str, Any]], columns: List[str], export: Dict[str, Any]) -> str:
        """将采集结果导出为 excel(.xlsx) 或 word(.docx)。返回最终文件路径。"""
        if not export:
            return ''
        fmt = str(export.get('format') or 'excel').lower()
        output_dir = export.get('outputDir') or str(Path.home())
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        file_name = str(export.get('fileName') or '').strip()
        if not file_name:
            file_name = f'webauto_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

        if not columns:
            # 兜底：从数据里收集列
            seen: List[str] = []
            for r in rows:
                for k in r.keys():
                    if k not in seen:
                        seen.append(k)
            columns = seen

        if fmt == 'word':
            from docx import Document
            if not file_name.lower().endswith('.docx'):
                file_name += '.docx'
            dest = out_dir / file_name
            doc = Document()
            table = doc.add_table(rows=1, cols=max(1, len(columns)))
            try:
                table.style = 'Table Grid'
            except Exception:
                pass
            hdr = table.rows[0].cells
            for i, col in enumerate(columns):
                hdr[i].text = str(col)
            for r in rows:
                cells = table.add_row().cells
                for i, col in enumerate(columns):
                    cells[i].text = str(r.get(col, ''))
            doc.save(str(dest))
            return str(dest)

        # 默认 excel
        from openpyxl import Workbook
        if not file_name.lower().endswith('.xlsx'):
            file_name += '.xlsx'
        dest = out_dir / file_name
        wb = Workbook()
        ws = wb.active
        ws.title = '采集结果'
        ws.append([str(c) for c in columns])
        for r in rows:
            ws.append([str(r.get(c, '')) for c in columns])
        wb.save(str(dest))
        return str(dest)

    # ------------------------------------------------------------------ #
    # 9. 采集状态（前端轮询）
    # ------------------------------------------------------------------ #
    def webauto_run_status(self):
        """返回采集任务实时状态及预览。"""
        try:
            self._wa_ensure()
            with self._wa_lock:
                st = self._wa_run
                return api_success(
                    running=bool(st['running']),
                    done=bool(st['done']),
                    success=bool(st['success']),
                    page=int(st['page']),
                    total=int(st['total']),
                    columns=list(st['columns']),
                    rows=[dict(r) for r in st['rows'][:50]],
                    outputPath=st['outputPath'],
                    error=st['error'],
                )
        except Exception as exc:
            return api_error(f'获取采集状态失败：{exc}')

    # ------------------------------------------------------------------ #
    # 10. 停止采集
    # ------------------------------------------------------------------ #
    def webauto_stop(self):
        """给采集线程发送停止信号。"""
        try:
            self._wa_ensure()
            self._wa_run_stop.set()
            return api_success('已发送停止信号')
        except Exception as exc:
            return api_error(f'停止采集失败：{exc}')

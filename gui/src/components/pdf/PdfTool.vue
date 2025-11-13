<template>
  <el-drawer
    v-model="visibleProxy"
    size="80%"
    append-to-body
    custom-class="pdf-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">PDF TOOLKIT</p>
          <h3>PDF 工具集</h3>
          <p class="sub">在一个面板内完成转换、扫描件、合并、拆分与页码切割</p>
        </div>
        <el-tag type="success" size="large">Beta</el-tag>
      </div>
    </template>
    <div class="pdf-tool">
      <el-tabs v-model="activeTab" class="pdf-tabs">
        <el-tab-pane label="PDF 转高清图片" name="image">
          <section class="panel">
            <header>
              <h4>输出每页高清图片</h4>
              <p>适合二次排版、打印或导入图像软件</p>
            </header>
            <el-form :model="state.toImage" label-width="110px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('toImage')">选择 PDF</el-button>
                  <span v-if="state.toImage.file" class="file-chip">{{ state.toImage.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="分辨率 (DPI)">
                <el-input-number v-model="state.toImage.dpi" :min="96" :max="600" />
              </el-form-item>
              <el-form-item label="图片格式">
                <el-select v-model="state.toImage.format" style="width: 160px">
                  <el-option label="PNG" value="png" />
                  <el-option label="JPG" value="jpg" />
                  <el-option label="TIFF" value="tiff" />
                  <el-option label="WEBP" value="webp" />
                </el-select>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.toImage.outputDir" placeholder="留空则与源文件同级" readonly />
                  <el-button @click="selectDir('toImage')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runConvertImages"
                >
                  开始转换
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.toImage.result.length" class="result-block">
              <p class="result-title">已生成图片</p>
              <el-scrollbar max-height="160px">
                <div class="result-list">
                  <el-tag
                    v-for="file in state.toImage.result"
                    :key="file"
                    type="info"
                    effect="plain"
                    @click="openPath(file)"
                  >
                    {{ file }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="PDF → 扫描件" name="scan">
          <section class="panel">
            <header>
              <h4>模拟扫描件效果</h4>
              <p>自动添加纸纹、微倾角和杂点，便于归档或走传统流程</p>
            </header>
            <el-form :model="state.scan" label-width="110px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('scan')">选择 PDF</el-button>
                  <span v-if="state.scan.file" class="file-chip">{{ state.scan.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="分辨率 (DPI)">
                <el-input-number v-model="state.scan.dpi" :min="120" :max="400" />
              </el-form-item>
              <el-form-item label="图片格式">
                <el-select v-model="state.scan.format" style="width: 160px">
                  <el-option label="JPG" value="jpg" />
                  <el-option label="PNG" value="png" />
                </el-select>
              </el-form-item>
              <el-form-item label="纸张纹理">
                <el-switch v-model="state.scan.texture" />
              </el-form-item>
              <el-form-item label="轻微倾斜">
                <el-switch v-model="state.scan.tilt" />
              </el-form-item>
              <el-form-item label="噪点强度">
                <el-slider v-model="state.scan.noise" :min="0" :max="10" :step="0.5" show-input />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.scan.outputDir" placeholder="留空则与源文件同级" readonly />
                  <el-button @click="selectDir('scan')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runScanEffect"
                >
                  生成扫描件
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.scan.result.length" class="result-block">
              <p class="result-title">输出图片</p>
              <el-scrollbar max-height="160px">
                <div class="result-list">
                  <el-tag
                    v-for="file in state.scan.result"
                    :key="file"
                    type="info"
                    effect="plain"
                    @click="openPath(file)"
                  >
                    {{ file }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="PDF 压缩" name="compress">
          <section class="panel">
            <header>
              <h4>按需压缩 PDF</h4>
            </header>
            <el-form :model="state.compress" label-width="110px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('compress')">选择 PDF</el-button>
                  <span v-if="state.compress.file" class="file-chip">{{ state.compress.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="压缩率">
                <div class="field-row field-wrap">
                  <el-radio-group v-model="state.compress.mode">
                    <el-radio-button label="low">低（高清）</el-radio-button>
                    <el-radio-button label="medium">中（均衡）</el-radio-button>
                    <el-radio-button label="high">高（小体积）</el-radio-button>
                    <el-radio-button label="custom">自定义</el-radio-button>
                  </el-radio-group>
                  <el-tag type="info" effect="plain">当前 DPI：{{ compressCurrentDpi }} DPI</el-tag>
                </div>
              </el-form-item>
              <el-form-item v-if="state.compress.mode === 'custom'" label="自定义 DPI">
                <el-input-number v-model="state.compress.customDpi" :min="72" :max="400" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.compress.outputDir" placeholder="可选" readonly />
                  <el-button @click="selectDir('compress')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item label="输出文件名">
                <el-input v-model="state.compress.outputName" placeholder="例如：压缩结果.pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runCompress"
                >
                  开始压缩
                </el-button>
              </el-form-item>
            </el-form>
            <p class="dpi-hint">
              推荐：低≈280 DPI（高清打印）、中≈200 DPI（通用传输）、高≈130 DPI（快速分享）。DPI 越低文件越小，越高越清晰。
            </p>
            <div v-if="state.compress.output" class="result-block">
              <p class="result-title">压缩后的 PDF</p>
              <el-scrollbar max-height="120px">
                <div class="result-list">
                  <el-tag
                    type="success"
                    effect="light"
                    @click="openPath(state.compress.output)"
                  >
                    {{ state.compress.output }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="合并 PDF" name="merge">
          <section class="panel">
            <header>
              <h4>将多个 PDF 合并</h4>
              <p>支持自定义顺序，生成单一归档文件</p>
            </header>
            <div class="merge-toolbar">
              <el-button @click="selectPdf('merge', true)">添加 PDF</el-button>
              <el-button text type="danger" @click="clearMerge">清空列表</el-button>
            </div>
            <el-table
              v-if="state.merge.files.length"
              :data="state.merge.files"
              size="small"
              border
            >
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="filename" label="文件名" />
              <el-table-column label="操作" width="180">
                <template #default="scope">
                  <el-button link type="primary" @click="moveMerge(scope.$index, -1)" :disabled="scope.$index === 0">上移</el-button>
                  <el-button link type="primary" @click="moveMerge(scope.$index, 1)" :disabled="scope.$index === state.merge.files.length - 1">下移</el-button>
                  <el-button link type="danger" @click="removeMerge(scope.$index)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="请先添加需要合并的 PDF" />
            <el-form label-width="110px" class="mt24">
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.merge.outputDir" placeholder="可选" readonly />
                  <el-button @click="selectDir('merge')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item label="输出文件名">
                <el-input v-model="state.merge.outputName" placeholder="例如：合并结果.pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :disabled="!state.merge.files.length"
                  :loading="state.loading"
                  @click="runMerge"
                >
                  合并 PDF
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.merge.output" class="result-block">
              <p class="result-title">输出文件</p>
              <el-scrollbar max-height="120px">
                <div class="result-list">
                  <el-tag
                    type="success"
                    effect="light"
                    @click="openPath(state.merge.output)"
                  >
                    {{ state.merge.output }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="拆分 PDF" name="split">
          <section class="panel">
            <header>
              <h4>按固定页数进行拆分</h4>
              <p>适合按章节或分页导出多个文件</p>
            </header>
            <el-form :model="state.split" label-width="110px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('split')">选择 PDF</el-button>
                  <span v-if="state.split.file" class="file-chip">{{ state.split.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="每个文件页数">
                <el-input-number v-model="state.split.pagesPerFile" :min="1" :max="50" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.split.outputDir" placeholder="留空则与源文件同级" readonly />
                  <el-button @click="selectDir('split')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runSplit"
                >
                  开始拆分
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.split.result.length" class="result-block">
              <p class="result-title">拆分结果</p>
              <el-scrollbar max-height="160px">
                <div class="result-list">
                  <el-tag
                    v-for="file in state.split.result"
                    :key="file"
                    type="info"
                    effect="plain"
                    @click="openPath(file)"
                  >
                    {{ file }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="页码切割" name="cut">
          <section class="panel">
            <header>
              <h4>按页码区间或自定义集合导出</h4>
              <p>快速摘取合同重点段落或指定页</p>
            </header>
            <el-form :model="state.cut" label-width="110px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('cut')">选择 PDF</el-button>
                  <span v-if="state.cut.file" class="file-chip">{{ state.cut.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="模式">
                <el-radio-group v-model="state.cut.mode">
                  <el-radio-button label="range">区间</el-radio-button>
                  <el-radio-button label="custom">指定页码</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.cut.mode === 'range'" label="起止页">
                <div class="field-row">
                  <el-input-number v-model="state.cut.startPage" :min="1" />
                  <span class="range-sep">至</span>
                  <el-input-number v-model="state.cut.endPage" :min="1" />
                </div>
              </el-form-item>
              <el-form-item v-else label="页码列表">
                <el-input
                  v-model="state.cut.pageSpec"
                  placeholder="示例：1-3,5,8"
                />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.cut.outputDir" placeholder="可选" readonly />
                  <el-button @click="selectDir('cut')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item label="输出文件名">
                <el-input v-model="state.cut.outputName" placeholder="例如：摘录.pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runCut"
                >
                  生成新 PDF
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.cut.output" class="result-block">
              <p class="result-title">生成文件</p>
              <el-scrollbar max-height="120px">
                <div class="result-list">
                  <el-tag
                    type="success"
                    effect="light"
                    @click="openPath(state.cut.output)"
                  >
                    {{ state.cut.output }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="页面重排" name="reorder">
          <section class="panel">
            <header>
              <h4>重新调整页码顺序</h4>
              <p>输入新的页码序列，可自动补全剩余页码</p>
            </header>
            <el-form :model="state.reorder" label-width="120px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('reorder')">选择 PDF</el-button>
                  <span v-if="state.reorder.file" class="file-chip">{{ state.reorder.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="页码顺序">
                <el-input
                  v-model="state.reorder.orderText"
                  placeholder="示例：3,1,2（表示新顺序）"
                />
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.reorder.appendRemaining">自动追加剩余页码</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runReorder">执行重排</el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.reorder.output" class="result-block">
              <p class="result-title">输出文件</p>
              <el-tag type="success" effect="plain" @click="openPath(state.reorder.output)">
                {{ state.reorder.output }}
              </el-tag>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="提取文本" name="text">
          <section class="panel">
            <header>
              <h4>导出 PDF 文本内容</h4>
              <p>支持纯文本、Markdown、HTML、Blocks 等模式</p>
            </header>
            <el-form :model="state.extractText" label-width="120px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('extractText')">选择 PDF</el-button>
                  <span v-if="state.extractText.file" class="file-chip">{{ state.extractText.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="模式">
                <el-radio-group v-model="state.extractText.mode">
                  <el-radio-button label="plain">纯文本</el-radio-button>
                  <el-radio-button label="markdown">Markdown</el-radio-button>
                  <el-radio-button label="html">HTML</el-radio-button>
                  <el-radio-button label="blocks">Blocks</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="页码区间">
                <div class="field-row">
                  <el-input-number v-model="state.extractText.startPage" :min="1" />
                  <span class="range-sep">至</span>
                  <el-input-number v-model="state.extractText.endPage" :min="1" />
                </div>
              </el-form-item>
              <el-form-item label="自定义页码">
                <el-input
                  v-model="state.extractText.pageSpec"
                  placeholder="可选，例如：1-3,5"
                />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.extractText.outputDir" placeholder="保存提取文本" readonly />
                  <el-button @click="selectDir('extractText')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.extractText.saveFile">保存为 .txt</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runExtractText">开始提取</el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.extractText.preview" class="result-block">
              <p class="result-title">文本预览</p>
              <el-input
                v-model="state.extractText.preview"
                type="textarea"
                :rows="8"
                readonly
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="提取图片" name="images">
          <section class="panel">
            <header>
              <h4>导出 PDF 内嵌图片</h4>
              <p>可指定页码范围与输出格式，自动保存到目录</p>
            </header>
            <el-form :model="state.extractImages" label-width="120px">
              <el-form-item label="源 PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('extractImages')">选择 PDF</el-button>
                  <span v-if="state.extractImages.file" class="file-chip">{{ state.extractImages.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="页码区间">
                <div class="field-row">
                  <el-input-number v-model="state.extractImages.startPage" :min="1" />
                  <span class="range-sep">至</span>
                  <el-input-number v-model="state.extractImages.endPage" :min="1" />
                </div>
              </el-form-item>
              <el-form-item label="自定义页码">
                <el-input v-model="state.extractImages.pageSpec" placeholder="可选：1-3,5" />
              </el-form-item>
              <el-form-item label="图片格式">
                <el-select v-model="state.extractImages.format" style="width: 160px">
                  <el-option label="PNG" value="png" />
                  <el-option label="JPG" value="jpg" />
                </el-select>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.extractImages.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('extractImages')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runExtractImages">
                  开始提取
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.extractImages.result.length" class="result-block">
              <p class="result-title">输出图片（部分）</p>
              <el-scrollbar max-height="160px">
                <div class="result-list">
                  <el-tag
                    v-for="file in state.extractImages.result"
                    :key="file"
                    type="info"
                    effect="plain"
                    @click="openPath(file)"
                  >
                    {{ file }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="图片转 PDF" name="imagePdf">
          <section class="panel">
            <header>
              <h4>将图片集合导出为 PDF</h4>
              <p>支持 1/2/4 图布局，自定义纸张与边距</p>
            </header>
            <div class="field-row">
              <el-button @click="addImagePdfFiles">添加图片</el-button>
              <el-button text type="danger" :disabled="!state.imagePdf.files.length" @click="clearImagePdf">
                清空
              </el-button>
            </div>
            <el-table
              v-if="state.imagePdf.files.length"
              :data="state.imagePdf.files"
              border
              size="small"
              style="margin: 12px 0"
            >
              <el-table-column type="index" width="50" label="#" />
              <el-table-column prop="filename" label="文件名" />
              <el-table-column label="操作" width="160">
                <template #default="scope">
                  <el-button link type="primary" @click="moveImagePdfFile(scope.$index, -1)" :disabled="scope.$index === 0">上移</el-button>
                  <el-button link type="primary" @click="moveImagePdfFile(scope.$index, 1)" :disabled="scope.$index === state.imagePdf.files.length - 1">下移</el-button>
                  <el-button link type="danger" @click="removeImagePdfFile(scope.$index)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-form :model="state.imagePdf" label-width="140px" class="form-gap">
              <el-form-item label="纸张尺寸">
                <el-select v-model="state.imagePdf.pageSize" style="width: 200px">
                  <el-option label="A4" value="a4" />
                  <el-option label="A5" value="a5" />
                  <el-option label="Letter" value="letter" />
                  <el-option label="自定义" value="custom" />
                </el-select>
              </el-form-item>
              <div v-if="state.imagePdf.pageSize === 'custom'" class="field-row">
                <el-form-item label="宽 (px)">
                  <el-input-number v-model="state.imagePdf.customWidth" :min="600" :max="6000" />
                </el-form-item>
                <el-form-item label="高 (px)">
                  <el-input-number v-model="state.imagePdf.customHeight" :min="600" :max="6000" />
                </el-form-item>
              </div>
              <el-form-item label="每页布局">
                <el-radio-group v-model="state.imagePdf.perPage">
                  <el-radio-button :label="1">1 / 页</el-radio-button>
                  <el-radio-button :label="2">2 / 页</el-radio-button>
                  <el-radio-button :label="4">4 / 页</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="边距 (px)">
                <el-input-number v-model="state.imagePdf.margin" :min="10" :max="200" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.imagePdf.outputDir" placeholder="留空自动创建" readonly />
                  <el-button @click="selectDir('imagePdf')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item label="输出文件名">
                <el-input v-model="state.imagePdf.outputName" placeholder="如：图片合集.pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  :disabled="!state.imagePdf.files.length"
                  @click="runImagesToPdf"
                >
                  生成 PDF
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.imagePdf.output" class="result-block">
              <p class="result-title">输出文件</p>
              <el-tag type="info" effect="plain" @click="openPath(state.imagePdf.output)">
                {{ state.imagePdf.output }}
              </el-tag>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>

      <section class="log-panel">
        <header>
          <h4>最近操作</h4>
          <p>保留最近 8 条，便于定位输出目录</p>
        </header>
        <el-timeline v-if="state.logs.length">
          <el-timeline-item
            v-for="item in state.logs"
            :key="item.id"
            :timestamp="item.time"
            :type="item.type"
            size="large"
          >
            <div class="log-entry">
              <strong>{{ item.message }}</strong>
              <p class="log-sub">{{ item.action }}</p>
              <el-link
                v-if="item.detail?.output"
                type="primary"
                @click="openPath(item.detail.output)"
              >
                打开输出
              </el-link>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无记录" />
      </section>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const activeTab = ref('image')

const compressModeDpiMap = {
  low: 280,
  medium: 200,
  high: 130
}

const imageFilter = ['图片 (*.png;*.jpg;*.jpeg;*.webp;*.bmp)']

const state = reactive({
  loading: false,
  toImage: {
    file: null,
    outputDir: '',
    dpi: 320,
    format: 'png',
    result: []
  },
  scan: {
    file: null,
    outputDir: '',
    dpi: 200,
    format: 'jpg',
    tilt: true,
    texture: true,
    noise: 6,
    result: []
  },
  compress: {
    file: null,
    mode: 'medium',
    customDpi: 200,
    outputDir: '',
    outputName: '压缩结果.pdf',
    output: ''
  },
  merge: {
    files: [],
    outputDir: '',
    outputName: '合并结果.pdf',
    output: ''
  },
  split: {
    file: null,
    outputDir: '',
    pagesPerFile: 1,
    result: []
  },
  cut: {
    file: null,
    outputDir: '',
    outputName: '摘录.pdf',
    mode: 'range',
    startPage: 1,
    endPage: 1,
    pageSpec: '',
    output: ''
  },
  reorder: {
    file: null,
    orderText: '',
    appendRemaining: true,
    output: ''
  },
  extractText: {
    file: null,
    mode: 'plain',
    startPage: 1,
    endPage: 1,
    pageSpec: '',
    outputDir: '',
    saveFile: false,
    preview: '',
    segments: []
  },
  extractImages: {
    file: null,
    startPage: 1,
    endPage: 1,
    pageSpec: '',
    format: 'png',
    outputDir: '',
    result: []
  },
  imagePdf: {
    files: [],
    pageSize: 'a4',
    customWidth: 2480,
    customHeight: 3508,
    perPage: 1,
    margin: 40,
    outputDir: '',
    outputName: '图片合集.pdf',
    output: ''
  },
  logs: []
})

const compressCurrentDpi = computed(() => {
  if (state.compress.mode === 'custom') {
    return state.compress.customDpi || 200
  }
  return compressModeDpiMap[state.compress.mode] || compressModeDpiMap.medium
})

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectPdf = async (key, multiple = false) => {
  if (!ensurePyReady()) return
  const result = await window.pywebview.api.system_pyCreateFileDialog(['PDF 文件 (*.pdf)'])
  if (!result || !result.length) return
  if (multiple) {
    const existing = new Set(state[key].files.map((item) => item.path))
    result.forEach((item) => {
      if (!existing.has(item.path)) {
        state[key].files.push(item)
      }
    })
  } else {
    state[key].file = result[0]
  }
}

const selectDir = async (key) => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state[key].outputDir || '')
  if (dir) {
    state[key].outputDir = dir
  }
}

const pushLog = (type, message, action, detail) => {
  state.logs.unshift({
    id: Date.now() + Math.random(),
    type,
    message,
    action,
    detail,
    time: new Date().toLocaleTimeString()
  })
  if (state.logs.length > 8) {
    state.logs.pop()
  }
}

const callApi = async (method, payload) => {
  if (!ensurePyReady()) return null
  const api = window.pywebview.api
  if (!api[method]) {
    ElMessage.error('当前客户端版本缺少 PDF 能力')
    return null
  }
  state.loading = true
  try {
    const res = await api[method](payload)
    if (res?.code === 0) {
      ElMessage.success(res.msg || '操作成功')
      pushLog('success', res.msg || '操作成功', method, res)
      return res
    } else {
      const msg = res?.msg || '操作失败'
      ElMessage.error(msg)
      pushLog('warning', msg, method, res)
      return null
    }
  } catch (error) {
    ElMessage.error(error.message || '执行失败')
    pushLog('danger', error.message || '执行失败', method)
    return null
  } finally {
    state.loading = false
  }
}

const openPath = async (path) => {
  if (!path || !ensurePyReady()) return
  window.pywebview.api.system_pyOpenFile(path)
}

const runConvertImages = async () => {
  if (!state.toImage.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_convert_to_images', {
    filePath: state.toImage.file.path,
    outputDir: state.toImage.outputDir,
    dpi: state.toImage.dpi,
    format: state.toImage.format
  })
  if (res) {
    state.toImage.result = res.files || []
  }
}

const runScanEffect = async () => {
  if (!state.scan.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_convert_to_scan', {
    filePath: state.scan.file.path,
    outputDir: state.scan.outputDir,
    dpi: state.scan.dpi,
    format: state.scan.format,
    tilt: state.scan.tilt,
    texture: state.scan.texture,
    noise: state.scan.noise
  })
  if (res) {
    state.scan.result = res.files || []
  }
}

const runCompress = async () => {
  if (!state.compress.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  if (state.compress.mode === 'custom') {
    const dpi = Number(state.compress.customDpi)
    if (!dpi) {
      ElMessage.warning('请输入自定义 DPI')
      return
    }
    if (dpi < 72 || dpi > 400) {
      ElMessage.warning('自定义 DPI 需在 72 - 400 之间')
      return
    }
  }
  const res = await callApi('pdf_compress', {
    filePath: state.compress.file.path,
    mode: state.compress.mode,
    customDpi: state.compress.customDpi,
    outputDir: state.compress.outputDir,
    outputName: state.compress.outputName
  })
  if (res) {
    state.compress.output = res.output
  }
}

const moveMerge = (index, offset) => {
  const target = index + offset
  if (target < 0 || target >= state.merge.files.length) return
  const list = state.merge.files
  const item = list[index]
  list.splice(index, 1)
  list.splice(target, 0, item)
}

const removeMerge = (index) => {
  state.merge.files.splice(index, 1)
}

const clearMerge = () => {
  state.merge.files.splice(0, state.merge.files.length)
}

const runMerge = async () => {
  if (!state.merge.files.length) {
    ElMessage.warning('请至少选择两个 PDF')
    return
  }
  const res = await callApi('pdf_merge', {
    files: state.merge.files.map((item) => item.path),
    outputDir: state.merge.outputDir,
    outputName: state.merge.outputName
  })
  if (res) {
    state.merge.output = res.output
  }
}

const runSplit = async () => {
  if (!state.split.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_split', {
    filePath: state.split.file.path,
    outputDir: state.split.outputDir,
    pagesPerFile: state.split.pagesPerFile
  })
  if (res) {
    state.split.result = res.files || []
  }
}

const runCut = async () => {
  if (!state.cut.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  if (state.cut.mode === 'custom' && !state.cut.pageSpec.trim()) {
    ElMessage.warning('请输入页码集合')
    return
  }
  const res = await callApi('pdf_cut', {
    filePath: state.cut.file.path,
    outputDir: state.cut.outputDir,
    outputName: state.cut.outputName,
    mode: state.cut.mode,
    startPage: state.cut.startPage,
    endPage: state.cut.endPage,
    pageSpec: state.cut.pageSpec
  })
  if (res) {
    state.cut.output = res.output
  }
}

const runReorder = async () => {
  if (!state.reorder.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const order = state.reorder.orderText
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((num) => Number.isInteger(num) && num > 0)
  if (!order.length) {
    ElMessage.warning('请填写新的页码顺序，例如：3,1,2')
    return
  }
  const res = await callApi('pdf_reorder_pages', {
    filePath: state.reorder.file.path,
    order,
    appendRemaining: state.reorder.appendRemaining
  })
  if (res) {
    state.reorder.output = res.output
  }
}

const runExtractText = async () => {
  if (!state.extractText.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_extract_text', {
    filePath: state.extractText.file.path,
    pageSpec: state.extractText.pageSpec,
    startPage: state.extractText.startPage,
    endPage: state.extractText.endPage,
    textMode: state.extractText.mode,
    saveFile: state.extractText.saveFile,
    outputDir: state.extractText.outputDir
  })
  if (res) {
    state.extractText.preview = res.preview || ''
    state.extractText.segments = res.segments || []
    if (res.output) {
      state.extractText.outputDir = res.output.split(/[\\/]/).slice(0, -1).join('/') || state.extractText.outputDir
    }
  }
}

const runExtractImages = async () => {
  if (!state.extractImages.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_extract_images', {
    filePath: state.extractImages.file.path,
    pageSpec: state.extractImages.pageSpec,
    startPage: state.extractImages.startPage,
    endPage: state.extractImages.endPage,
    format: state.extractImages.format,
    outputDir: state.extractImages.outputDir
  })
  if (res) {
    state.extractImages.result = res.files || []
    state.extractImages.outputDir = res.outputDir || state.extractImages.outputDir
  }
}

const addImagePdfFiles = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(imageFilter)
  if (files?.length) {
    state.imagePdf.files.push(...files)
  }
}

const removeImagePdfFile = (index) => {
  state.imagePdf.files.splice(index, 1)
}

const moveImagePdfFile = (index, offset) => {
  const target = index + offset
  if (target < 0 || target >= state.imagePdf.files.length) return
  const list = state.imagePdf.files
  const current = list[index]
  list.splice(index, 1)
  list.splice(target, 0, current)
}

const clearImagePdf = () => {
  state.imagePdf.files.splice(0, state.imagePdf.files.length)
}

const runImagesToPdf = async () => {
  if (!state.imagePdf.files.length) {
    ElMessage.warning('请先选择图片')
    return
  }
  const res = await callApi('pdf_images_to_pdf', {
    images: state.imagePdf.files.map((item) => item.path),
    pageSize: state.imagePdf.pageSize,
    customWidth: state.imagePdf.customWidth,
    customHeight: state.imagePdf.customHeight,
    perPage: state.imagePdf.perPage,
    margin: state.imagePdf.margin,
    outputDir: state.imagePdf.outputDir,
    outputName: state.imagePdf.outputName
  })
  if (res) {
    state.imagePdf.output = res.output
  }
}
</script>

<style scoped>
.pdf-tool-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding-bottom: 0;
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  width: 100%;
}

.drawer-head h3 {
  margin: 4px 0;
  font-size: 24px;
}

.drawer-head .eyebrow {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.2em;
  color: #9094a6;
}

.drawer-head .sub {
  margin: 0;
  color: #6c7185;
  font-size: 14px;
}

.pdf-tool {
  padding-right: 12px;
}

.pdf-tabs {
  margin-bottom: 20px;
}

.panel {
  background: #fdfdff;
  padding: 20px;
  border: 1px solid #edf0f5;
  border-radius: 18px;
  margin-bottom: 24px;
}

.panel header {
  margin-bottom: 16px;
}

.panel header h4 {
  margin: 0;
}

.panel header p {
  margin: 6px 0 0;
  color: #7a8093;
  font-size: 13px;
}

.field-row {
  display: flex;
  gap: 12px;
  flex: 1;
  align-items: center;
}

.field-wrap {
  flex-wrap: wrap;
  gap: 8px;
}

.dpi-hint {
  margin: 8px 0 0;
  color: #7a8093;
  font-size: 13px;
}

.file-chip {
  padding: 6px 10px;
  border-radius: 8px;
  background: #eef2ff;
  color: #4058d7;
  font-size: 13px;
}

.result-block {
  margin-top: 16px;
}

.result-title {
  margin: 0 0 10px;
  font-weight: 600;
  color: #4d5366;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.merge-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.mt24 {
  margin-top: 24px;
}

.range-sep {
  color: #9094a6;
}

.log-panel {
  background: #fff;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #edf0f5;
}

.log-panel header {
  margin-bottom: 12px;
}

.log-panel header h4 {
  margin: 0;
}

.log-panel header p {
  margin: 4px 0 0;
  color: #9498aa;
  font-size: 13px;
}

.log-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-entry .log-sub {
  margin: 0;
  color: #99a0b3;
  font-size: 12px;
}
</style>

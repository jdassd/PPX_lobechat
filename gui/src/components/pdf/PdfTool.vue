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
          <h3>PDF 宸ュ叿闆?/h3>
          <p class="sub">鍦ㄤ竴涓潰鏉垮唴瀹屾垚杞崲銆佹壂鎻忎欢銆佸悎骞躲€佹媶鍒嗕笌椤电爜鍒囧壊</p>
        </div>
      </div>
    </template>
    <div class="pdf-tool">
      <el-tabs v-model="activeTab" class="pdf-tabs">
        <el-tab-pane label="PDF 杞珮娓呭浘鐗? name="image">
          <section class="panel">
            <header>
              <h4>杈撳嚭姣忛〉楂樻竻鍥剧墖</h4>
              <p>閫傚悎浜屾鎺掔増銆佹墦鍗版垨瀵煎叆鍥惧儚杞欢</p>
            </header>
            <el-form :model="state.toImage" label-width="110px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('toImage')">閫夋嫨 PDF</el-button>
                  <span v-if="state.toImage.file" class="file-chip">{{ state.toImage.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="鍒嗚鲸鐜?(DPI)">
                <div class="field-row field-wrap">
                  <el-radio-group v-model="state.toImage.dpiPreset">
                    <el-radio-button label="ultra">瓒呮竻</el-radio-button>
                    <el-radio-button label="high">楂樻竻</el-radio-button>
                    <el-radio-button label="standard">鏍囨竻</el-radio-button>
                    <el-radio-button label="custom">鑷畾涔?/el-radio-button>
                  </el-radio-group>
                  <el-input-number
                    v-model="state.toImage.dpi"
                    :min="96"
                    :max="600"
                    :step="10"
                    :disabled="state.toImage.dpiPreset !== 'custom'"
                  />
                </div>
                <p class="dpi-hint">
                  DPI 瓒婇珮锛屽鍑哄浘鐗囪秺娓呮櫚锛屾枃浠朵綋绉篃浼氭洿澶с€傛帹鑽愶細瓒呮竻 400 DPI锛岄珮娓?300 DPI锛屾爣娓?200 DPI銆?
                </p>
              </el-form-item>
              <el-form-item label="鍥剧墖鏍煎紡">
                <el-select v-model="state.toImage.format" style="width: 160px">
                  <el-option label="PNG" value="png" />
                  <el-option label="JPG" value="jpg" />
                  <el-option label="GIF" value="gif" />
                  <el-option label="SVG" value="svg" />
                  <el-option label="TIFF" value="tiff" />
                  <el-option label="WEBP" value="webp" />
                </el-select>
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.toImage.outputDir" placeholder="鐣欑┖鍒欎笌婧愭枃浠跺悓绾? readonly />
                  <el-button @click="selectDir('toImage')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runConvertImages"
                >
                  寮€濮嬭浆鎹?
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.toImage.result.length" class="result-block">
              <p class="result-title">宸茬敓鎴愬浘鐗?/p>
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

        <el-tab-pane label="PDF 鈫?鎵弿浠? name="scan">
          <section class="panel">
            <header>
              <h4>妯℃嫙鎵弿浠舵晥鏋?/h4>
              <p>鑷姩娣诲姞绾哥汗銆佸井鍊捐鍜屾潅鐐癸紝渚夸簬褰掓。鎴栬蛋浼犵粺娴佺▼</p>
            </header>
            <el-form :model="state.scan" label-width="110px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('scan')">閫夋嫨 PDF</el-button>
                  <span v-if="state.scan.file" class="file-chip">{{ state.scan.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="鍒嗚鲸鐜?(DPI)">
                <el-input-number v-model="state.scan.dpi" :min="120" :max="400" />
              </el-form-item>
              <el-form-item label="鍥剧墖鏍煎紡">
                <el-select v-model="state.scan.format" style="width: 160px">
                  <el-option label="JPG" value="jpg" />
                  <el-option label="PNG" value="png" />
                </el-select>
              </el-form-item>
              <el-form-item label="绾稿紶绾圭悊">
                <el-switch v-model="state.scan.texture" />
              </el-form-item>
              <el-form-item label="杞诲井鍊炬枩">
                <el-switch v-model="state.scan.tilt" />
              </el-form-item>
              <el-form-item label="鍣偣寮哄害">
                <el-slider v-model="state.scan.noise" :min="0" :max="10" :step="0.5" show-input />
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.scan.outputDir" placeholder="鐣欑┖鍒欎笌婧愭枃浠跺悓绾? readonly />
                  <el-button @click="selectDir('scan')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runScanEffect"
                >
                  鐢熸垚鎵弿浠?
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.scan.result.length" class="result-block">
              <p class="result-title">杈撳嚭鍥剧墖</p>
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

        <el-tab-pane label="PDF 鍘嬬缉" name="compress">
          <section class="panel">
            <header>
              <h4>鎸夐渶鍘嬬缉 PDF</h4>
            </header>
            <el-form :model="state.compress" label-width="110px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('compress')">閫夋嫨 PDF</el-button>
                  <span v-if="state.compress.file" class="file-chip">{{ state.compress.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="鍘嬬缉鐜?>
                <div class="field-row field-wrap">
                  <el-radio-group v-model="state.compress.mode">
                    <el-radio-button label="low">浣庯紙楂樻竻锛?/el-radio-button>
                    <el-radio-button label="medium">涓紙鍧囪　锛?/el-radio-button>
                    <el-radio-button label="high">楂橈紙灏忎綋绉級</el-radio-button>
                    <el-radio-button label="custom">鑷畾涔?/el-radio-button>
                  </el-radio-group>
                  <el-tag type="info" effect="plain">褰撳墠 DPI锛歿{ compressCurrentDpi }} DPI</el-tag>
                </div>
              </el-form-item>
              <el-form-item v-if="state.compress.mode === 'custom'" label="鑷畾涔?DPI">
                <el-input-number v-model="state.compress.customDpi" :min="72" :max="400" />
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.compress.outputDir" placeholder="鍙€? readonly />
                  <el-button @click="selectDir('compress')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鏂囦欢鍚?>
                <el-input v-model="state.compress.outputName" placeholder="渚嬪锛氬帇缂╃粨鏋?pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runCompress"
                >
                  寮€濮嬪帇缂?
                </el-button>
              </el-form-item>
            </el-form>
            <p class="dpi-hint">
              鎺ㄨ崘锛氫綆鈮?80 DPI锛堥珮娓呮墦鍗帮級銆佷腑鈮?00 DPI锛堥€氱敤浼犺緭锛夈€侀珮鈮?30 DPI锛堝揩閫熷垎浜級銆侱PI 瓒婁綆鏂囦欢瓒婂皬锛岃秺楂樿秺娓呮櫚銆?
            </p>
            <div v-if="state.compress.output" class="result-block">
              <p class="result-title">鍘嬬缉鍚庣殑 PDF</p>
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

        <el-tab-pane label="鍚堝苟 PDF" name="merge">
          <section class="panel">
            <header>
              <h4>灏嗗涓?PDF 鍚堝苟</h4>
              <p>鏀寔鑷畾涔夐『搴忥紝鐢熸垚鍗曚竴褰掓。鏂囦欢</p>
            </header>
            <div class="merge-toolbar">
              <el-button @click="selectPdf('merge', true)">娣诲姞 PDF</el-button>
              <el-button text type="danger" @click="clearMerge">娓呯┖鍒楄〃</el-button>
            </div>
            <el-table
              v-if="state.merge.files.length"
              :data="state.merge.files"
              size="small"
              border
            >
              <el-table-column type="index" label="#" width="50" />
              <el-table-column label="椤电爜閫夋嫨" width="220">
                <template #default="scope">
                  <el-input
                    v-model="scope.row.pageSpec"
                    size="small"
                    placeholder="濡?1-3,5,8"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="filename" label="鏂囦欢鍚? />
              <el-table-column label="鎿嶄綔" width="180">
                <template #default="scope">
                  <el-button link type="primary" @click="moveMerge(scope.$index, -1)" :disabled="scope.$index === 0">涓婄Щ</el-button>
                  <el-button link type="primary" @click="moveMerge(scope.$index, 1)" :disabled="scope.$index === state.merge.files.length - 1">涓嬬Щ</el-button>
                  <el-button link type="danger" @click="removeMerge(scope.$index)">绉婚櫎</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="璇峰厛娣诲姞闇€瑕佸悎骞剁殑 PDF" />
            <el-form label-width="110px" class="mt24">
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.merge.outputDir" placeholder="鍙€? readonly />
                  <el-button @click="selectDir('merge')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鏂囦欢鍚?>
                <el-input v-model="state.merge.outputName" placeholder="渚嬪锛氬悎骞剁粨鏋?pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :disabled="!state.merge.files.length"
                  :loading="state.loading"
                  @click="runMerge"
                >
                  鍚堝苟 PDF
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.merge.output" class="result-block">
              <p class="result-title">杈撳嚭鏂囦欢</p>
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

        <el-tab-pane label="鎷嗗垎 PDF" name="split">
          <section class="panel">
            <header>
              <h4>鎷嗗垎妯″紡涓€锛氭寜鍥哄畾椤垫暟鎷嗗垎</h4>
              <p>姣?N 椤垫媶鍒嗘垚涓€涓枃浠讹紝閫傚悎鎸夌珷鑺傛垨鍒嗛〉瀵煎嚭澶氫釜 PDF</p>
            </header>
            <el-form :model="state.split" label-width="110px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('split')">閫夋嫨 PDF</el-button>
                  <span v-if="state.split.file" class="file-chip">{{ state.split.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="姣忎釜鏂囦欢椤垫暟">
                <el-input-number v-model="state.split.pagesPerFile" :min="1" :max="50" />
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.split.outputDir" placeholder="鐣欑┖鍒欎笌婧愭枃浠跺悓绾? readonly />
                  <el-button @click="selectDir('split')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runSplit"
                >
                  寮€濮嬫媶鍒?
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.split.result.length" class="result-block">
              <p class="result-title">鎷嗗垎缁撴灉</p>
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

        <el-tab-pane label="椤电爜鍒囧壊" name="cut">
          <section class="panel">
            <header>
              <h4>鎷嗗垎妯″紡浜岋細鎸夐〉鐮佹媶鍒?/ 鎽樺彇</h4>
              <p>閫氳繃椤电爜鍖洪棿鎴栬嚜瀹氫箟椤电爜鍒楄〃鎽樺彇椤甸潰锛岀敓鎴愪竴浠芥柊鐨?PDF 鎽樺綍</p>
            </header>
            <el-form :model="state.cut" label-width="110px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('cut')">閫夋嫨 PDF</el-button>
                  <span v-if="state.cut.file" class="file-chip">{{ state.cut.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="妯″紡">
                <el-radio-group v-model="state.cut.mode">
                  <el-radio-button label="range">鍖洪棿</el-radio-button>
                  <el-radio-button label="custom">鎸囧畾椤电爜</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.cut.mode === 'range'" label="璧锋椤?>
                <div class="field-row">
                  <el-input-number v-model="state.cut.startPage" :min="1" />
                  <span class="range-sep">鑷?/span>
                  <el-input-number v-model="state.cut.endPage" :min="1" />
                </div>
              </el-form-item>
              <el-form-item v-else label="椤电爜鍒楄〃">
                <el-input
                  v-model="state.cut.pageSpec"
                  placeholder="绀轰緥锛?-3,5,8锛涙敮鎸佺敤鍒嗗彿鎴栨崲琛屽垎闅斿涓尯闂?
                  type="textarea"
                  :rows="3"
                />
              </el-form-item>
              <el-form-item v-if="state.cut.mode === 'custom'">
                <el-checkbox v-model="state.cut.multi">
                  鎸夊涓尯闂村垎鍒鍑哄涓?PDF 鏂囦欢
                </el-checkbox>
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.cut.outputDir" placeholder="鍙€? readonly />
                  <el-button @click="selectDir('cut')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鏂囦欢鍚?>
                <el-input v-model="state.cut.outputName" placeholder="渚嬪锛氭憳褰?pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  @click="runCut"
                >
                  鐢熸垚鏂?PDF
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.cut.output || state.cut.outputs.length" class="result-block">
              <p class="result-title">鐢熸垚鏂囦欢</p>
              <el-scrollbar max-height="120px">
                <div class="result-list">
                  <el-tag
                    v-for="file in (state.cut.outputs.length ? state.cut.outputs : [state.cut.output])"
                    :key="file"
                    type="success"
                    effect="light"
                    @click="openPath(file)"
                  >
                    {{ file }}
                  </el-tag>
                </div>
              </el-scrollbar>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="椤甸潰閲嶆帓" name="reorder">
          <section class="panel">
            <header>
              <h4>鎷栧姩缂╃暐鍥捐皟鏁撮〉闈㈤『搴?/h4>
              <p>鍏堢敓鎴愰瑙堬紝鍐嶉€氳繃鎷栧姩椤甸潰缂╃暐鍥鹃噸鎺掗『搴忥紝鏃犻渶鎵嬪姩濉啓椤电爜</p>
            </header>
            <el-form :model="state.reorder" label-width="120px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('reorder')">閫夋嫨 PDF</el-button>
                  <span v-if="state.reorder.file" class="file-chip">{{ state.reorder.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="椤甸潰棰勮">
                <div class="reorder-preview">
                  <div class="field-row">
                    <el-button
                      type="primary"
                      plain
                      :loading="state.reorder.loadingPreview"
                      :disabled="!state.reorder.file"
                      @click="loadReorderPreview"
                    >
                      鐢熸垚棰勮
                    </el-button>
                    <span class="reorder-hint">鐢熸垚鍚庡彲鍦ㄤ笅鏂规嫋鍔ㄩ〉闈㈢缉鐣ュ浘璋冩暣椤哄簭锛堝綋鍓嶉瑙堟渶澶氬墠 80 椤碉級</span>
                  </div>
                  <template v-if="state.reorder.pages && state.reorder.pages.length">
                    <el-scrollbar max-height="260px">
                      <div class="reorder-grid">
                        <div
                          v-for="(page, index) in state.reorder.pages"
                          :key="page.page"
                          class="reorder-page"
                          draggable="true"
                          @dragstart="onReorderDragStart(index, $event)"
                          @dragover.prevent="onReorderDragOver(index, $event)"
                          @drop.prevent="onReorderDrop(index, $event)"
                        >
                          <div class="reorder-thumb">
                            <img :src="page.image" :alt="`绗?${page.page} 椤礰" />
                          </div>
                          <p class="reorder-page-label">绗?{{ page.page }} 椤?/p>
                        </div>
                      </div>
                    </el-scrollbar>
                    <p class="reorder-hint">褰撳墠椤哄簭鍗充负閲嶆帓鍚庣殑椤哄簭锛屾墽琛屽墠鍙娆¤皟鏁淬€?/p>
                  </template>
                  <p v-else class="reorder-empty-hint">璇烽€夋嫨 PDF 鍚庣偣鍑烩€滅敓鎴愰瑙堚€濄€?/p>
                </div>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.reorder.appendRemaining">鑷姩杩藉姞鍓╀綑椤电爜</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runReorder">鎵ц閲嶆帓</el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.reorder.output" class="result-block">
              <p class="result-title">杈撳嚭鏂囦欢</p>
              <el-tag type="success" effect="plain" @click="openPath(state.reorder.output)">
                {{ state.reorder.output }}
              </el-tag>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鎻愬彇鏂囨湰" name="text">
          <section class="panel">
            <header>
              <h4>瀵煎嚭 PDF 鏂囨湰鍐呭</h4>
              <p>鏀寔绾枃鏈€丮arkdown銆丠TML銆丅locks 绛夋ā寮?/p>
            </header>
            <el-form :model="state.extractText" label-width="120px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('extractText')">閫夋嫨 PDF</el-button>
                  <span v-if="state.extractText.file" class="file-chip">{{ state.extractText.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="妯″紡">
                <el-radio-group v-model="state.extractText.mode">
                  <el-radio-button label="plain">绾枃鏈?/el-radio-button>
                  <el-radio-button label="markdown">Markdown</el-radio-button>
                  <el-radio-button label="html">HTML</el-radio-button>
                  <el-radio-button label="blocks">Blocks</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="椤电爜鍖洪棿">
                <div class="field-row">
                  <el-input-number v-model="state.extractText.startPage" :min="1" />
                  <span class="range-sep">鑷?/span>
                  <el-input-number v-model="state.extractText.endPage" :min="1" />
                </div>
              </el-form-item>
              <el-form-item label="鑷畾涔夐〉鐮?>
                <el-input
                  v-model="state.extractText.pageSpec"
                  placeholder="鍙€夛紝渚嬪锛?-3,5"
                />
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.extractText.outputDir" placeholder="淇濆瓨鎻愬彇鏂囨湰" readonly />
                  <el-button @click="selectDir('extractText')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.extractText.saveFile">淇濆瓨涓?.txt</el-checkbox>
              </el-form-item>
              <el-form-item>
              <el-button type="primary" :loading="state.loading" @click="runExtractText">寮€濮嬫彁鍙?/el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.extractText.preview" class="result-block">
              <p class="result-title">鏂囨湰棰勮</p>
              <el-input
                v-model="state.extractText.preview"
                type="textarea"
                :rows="8"
                readonly
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鐢熸垚鐩綍" name="toc">
          <section class="panel">
            <header>
              <h4>涓?PDF 鑷姩鐢熸垚鐩綍</h4>
              <p>鏍规嵁姣忛〉鏍囬鑷姩鎺ㄦ柇鐩綍锛屽苟鐢熸垚涓€浠藉甫鐩綍鐨?PDF</p>
            </header>
            <el-form :model="state.toc" label-width="120px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('toc')">閫夋嫨 PDF</el-button>
                  <span v-if="state.toc.file" class="file-chip">{{ state.toc.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.toc.outputDir" placeholder="淇濆瓨甯︾洰褰曠殑 PDF" readonly />
                  <el-button @click="selectDir('toc')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鏂囦欢鍚?>
                <el-input v-model="state.toc.outputName" placeholder="濡傦細甯︾洰褰曠増.pdf" />
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.toc.saveText">鍚屾椂瀵煎嚭鐩綍涓?.txt</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runGenerateToc">
                  鐢熸垚鐩綍
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.toc.output" class="result-block">
              <p class="result-title">杈撳嚭鏂囦欢</p>
              <el-tag type="success" effect="plain" @click="openPath(state.toc.output)">
                {{ state.toc.output }}
              </el-tag>
              <p v-if="state.toc.textOutput" class="result-title" style="margin-top: 8px">
                鐩綍鏂囨湰宸插彟瀛樹负锛?
                <a class="link" @click.prevent="openPath(state.toc.textOutput)">{{ state.toc.textOutput }}</a>
              </p>
            </div>
            <div v-if="state.toc.preview" class="result-block">
              <p class="result-title">鐩綍棰勮</p>
              <el-input
                v-model="state.toc.preview"
                type="textarea"
                :rows="8"
                readonly
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="PDF 杞?Word" name="word">
          <section class="panel">
            <header>
              <h4>杞崲涓哄彲缂栬緫 Word 鏂囨。</h4>
              <p>鎸夐〉鎻愬彇鏂囨湰骞剁敓鎴?.docx锛岄€傚悎鍐嶆鎺掔増缂栬緫</p>
            </header>
            <el-form :model="state.word" label-width="120px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('word')">閫夋嫨 PDF</el-button>
                  <span v-if="state.word.file" class="file-chip">{{ state.word.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="鏂囨湰妯″紡">
                <el-radio-group v-model="state.word.textMode">
                  <el-radio-button label="plain">绾枃鏈?/el-radio-button>
                  <el-radio-button label="markdown">Markdown</el-radio-button>
                  <el-radio-button label="html">HTML</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.word.outputDir" placeholder="淇濆瓨鐢熸垚鐨?.docx" readonly />
                  <el-button @click="selectDir('word')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runPdfToWord">
                  杞崲涓?Word
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.word.output" class="result-block">
              <p class="result-title">杈撳嚭鏂囦欢</p>
              <el-tag type="success" effect="plain" @click="openPath(state.word.output)">
                {{ state.word.output }}
              </el-tag>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鎻愬彇鍥剧墖" name="images">
          <section class="panel">
            <header>
              <h4>瀵煎嚭 PDF 鍐呭祵鍥剧墖</h4>
              <p>鍙寚瀹氶〉鐮佽寖鍥翠笌杈撳嚭鏍煎紡锛岃嚜鍔ㄤ繚瀛樺埌鐩綍</p>
            </header>
            <el-form :model="state.extractImages" label-width="120px">
              <el-form-item label="婧?PDF">
                <div class="field-row">
                  <el-button @click="selectPdf('extractImages')">閫夋嫨 PDF</el-button>
                  <span v-if="state.extractImages.file" class="file-chip">{{ state.extractImages.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item label="椤电爜鍖洪棿">
                <div class="field-row">
                  <el-input-number v-model="state.extractImages.startPage" :min="1" />
                  <span class="range-sep">鑷?/span>
                  <el-input-number v-model="state.extractImages.endPage" :min="1" />
                </div>
              </el-form-item>
              <el-form-item label="鑷畾涔夐〉鐮?>
                <el-input v-model="state.extractImages.pageSpec" placeholder="鍙€夛細1-3,5" />
              </el-form-item>
              <el-form-item label="鍥剧墖鏍煎紡">
                <el-select v-model="state.extractImages.format" style="width: 160px">
                  <el-option label="PNG" value="png" />
                  <el-option label="JPG" value="jpg" />
                </el-select>
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.extractImages.outputDir" placeholder="鑷姩鍒涘缓" readonly />
                  <el-button @click="selectDir('extractImages')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runExtractImages">
                  寮€濮嬫彁鍙?
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.extractImages.result.length" class="result-block">
              <p class="result-title">杈撳嚭鍥剧墖锛堥儴鍒嗭級</p>
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

        <el-tab-pane label="鍥剧墖杞?PDF" name="imagePdf">
          <section class="panel">
            <header>
              <h4>灏嗗浘鐗囬泦鍚堝鍑轰负 PDF</h4>
              <p>鏀寔 1/2/4 鍥惧竷灞€锛岃嚜瀹氫箟绾稿紶涓庤竟璺?/p>
            </header>
            <p class="image-pdf-hint">涓庡浘鐗囧伐鍏蜂腑鐨勩€屽浘鐗囪浆 PDF銆嶅姛鑳界瓑浠凤紝杩欓噷浠呮彁渚涗竴涓揩鎹峰叆鍙ｃ€?/p>
            <div class="field-row">
              <el-button @click="addImagePdfFiles">娣诲姞鍥剧墖</el-button>
              <el-button text type="danger" :disabled="!state.imagePdf.files.length" @click="clearImagePdf">
                娓呯┖
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
              <el-table-column prop="filename" label="鏂囦欢鍚? />
              <el-table-column label="鎿嶄綔" width="160">
                <template #default="scope">
                  <el-button link type="primary" @click="moveImagePdfFile(scope.$index, -1)" :disabled="scope.$index === 0">涓婄Щ</el-button>
                  <el-button link type="primary" @click="moveImagePdfFile(scope.$index, 1)" :disabled="scope.$index === state.imagePdf.files.length - 1">涓嬬Щ</el-button>
                  <el-button link type="danger" @click="removeImagePdfFile(scope.$index)">绉婚櫎</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-form :model="state.imagePdf" label-width="140px" class="form-gap">
              <el-form-item label="绾稿紶灏哄">
                <el-select v-model="state.imagePdf.pageSize" style="width: 200px">
                  <el-option label="A4" value="a4" />
                  <el-option label="A5" value="a5" />
                  <el-option label="Letter" value="letter" />
                  <el-option label="鑷畾涔? value="custom" />
                </el-select>
              </el-form-item>
              <div v-if="state.imagePdf.pageSize === 'custom'" class="field-row">
                <el-form-item label="瀹?(px)">
                  <el-input-number v-model="state.imagePdf.customWidth" :min="600" :max="6000" />
                </el-form-item>
                <el-form-item label="楂?(px)">
                  <el-input-number v-model="state.imagePdf.customHeight" :min="600" :max="6000" />
                </el-form-item>
              </div>
              <el-form-item label="姣忛〉甯冨眬">
                <el-radio-group v-model="state.imagePdf.perPage">
                  <el-radio-button :label="1">1 / 椤?/el-radio-button>
                  <el-radio-button :label="2">2 / 椤?/el-radio-button>
                  <el-radio-button :label="4">4 / 椤?/el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="杈硅窛 (px)">
                <el-input-number v-model="state.imagePdf.margin" :min="10" :max="200" />
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.imagePdf.outputDir" placeholder="鐣欑┖鑷姩鍒涘缓" readonly />
                  <el-button @click="selectDir('imagePdf')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鏂囦欢鍚?>
                <el-input v-model="state.imagePdf.outputName" placeholder="濡傦細鍥剧墖鍚堥泦.pdf" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  :disabled="!state.imagePdf.files.length"
                  @click="runImagesToPdf"
                >
                  鐢熸垚 PDF
                </el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.imagePdf.output" class="result-block">
              <p class="result-title">杈撳嚭鏂囦欢</p>
              <el-tag type="info" effect="plain" @click="openPath(state.imagePdf.output)">
                {{ state.imagePdf.output }}
              </el-tag>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>

      <section class="log-panel">
        <header>
          <h4>鏈€杩戞搷浣?/h4>
          <p>淇濈暀鏈€杩?8 鏉★紝渚夸簬瀹氫綅杈撳嚭鐩綍</p>
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
                鎵撳紑杈撳嚭
              </el-link>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="鏆傛棤璁板綍" />
      </section>
    </div>
  </el-drawer>
</template>

<script setup>
  import { computed, reactive, ref, watch } from 'vue'
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

const toImageDpiPresetMap = {
  ultra: 400,
  high: 300,
  standard: 200
}

const imageFilter = ['鍥剧墖 (*.png;*.jpg;*.jpeg;*.webp;*.bmp)']

const state = reactive({
  loading: false,
  toImage: {
    file: null,
    outputDir: '',
    dpiPreset: 'ultra',
    dpi: 400,
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
    outputName: '鍘嬬缉缁撴灉.pdf',
    output: ''
  },
  merge: {
    files: [],
    outputDir: '',
    outputName: '鍚堝苟缁撴灉.pdf',
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
    outputName: '鎽樺綍.pdf',
    mode: 'range',
    startPage: 1,
    endPage: 1,
    pageSpec: '',
    multi: false,
    output: '',
    outputs: []
  },
  reorder: {
    file: null,
    orderText: '',
    appendRemaining: true,
    output: '',
    pages: [],
    loadingPreview: false
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
  toc: {
    file: null,
    outputDir: '',
    outputName: '甯︾洰褰曠増.pdf',
    saveText: false,
    preview: '',
    output: '',
    textOutput: ''
  },
  word: {
    file: null,
    textMode: 'plain',
    outputDir: '',
    output: ''
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
    outputName: '鍥剧墖鍚堥泦.pdf',
    output: ''
  },
  logs: []
})

const reorderDragState = reactive({
  fromIndex: -1
})

const compressCurrentDpi = computed(() => {
  if (state.compress.mode === 'custom') {
    return state.compress.customDpi || 200
  }
  return compressModeDpiMap[state.compress.mode] || compressModeDpiMap.medium
})

watch(
  () => state.toImage.dpiPreset,
  (preset) => {
    if (preset === 'custom') return
    const target = toImageDpiPresetMap[preset]
    if (target) {
      state.toImage.dpi = target
    }
  }
)

watch(
  () => state.toImage.dpi,
  (value) => {
    if (state.toImage.dpiPreset === 'custom') return
    const presetValue = toImageDpiPresetMap[state.toImage.dpiPreset]
    if (presetValue && value !== presetValue) {
      state.toImage.dpiPreset = 'custom'
    }
  }
)

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('璇ュ姛鑳介渶鍦ㄦ闈㈠鎴风涓娇鐢?)
    return false
  }
  return true
}

const selectPdf = async (key, multiple = false) => {
  if (!ensurePyReady()) return
  const result = await window.pywebview.api.system_pyCreateFileDialog(['PDF 鏂囦欢 (*.pdf)'])
  if (!result || !result.length) return
  if (multiple) {
    const existing = new Set(state[key].files.map((item) => item.path))
    result.forEach((item) => {
      if (!existing.has(item.path)) {
        const entry = { ...item }
        if (key === 'merge' && entry.pageSpec === undefined) {
          entry.pageSpec = ''
        }
        state[key].files.push(entry)
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
    ElMessage.error('褰撳墠瀹㈡埛绔増鏈己灏?PDF 鑳藉姏')
    return null
  }
  state.loading = true
  try {
    const res = await api[method](payload)
    if (res?.code === 0) {
      ElMessage.success(res.msg || '鎿嶄綔鎴愬姛')
      pushLog('success', res.msg || '鎿嶄綔鎴愬姛', method, res)
      return res
    } else {
      const msg = res?.msg || '鎿嶄綔澶辫触'
      ElMessage.error(msg)
      pushLog('warning', msg, method, res)
      return null
    }
  } catch (error) {
    ElMessage.error(error.message || '鎵ц澶辫触')
    pushLog('danger', error.message || '鎵ц澶辫触', method)
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
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
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
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
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
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
    return
  }
  if (state.compress.mode === 'custom') {
    const dpi = Number(state.compress.customDpi)
    if (!dpi) {
      ElMessage.warning('璇疯緭鍏ヨ嚜瀹氫箟 DPI')
      return
    }
    if (dpi < 72 || dpi > 400) {
      ElMessage.warning('鑷畾涔?DPI 闇€鍦?72 - 400 涔嬮棿')
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
    ElMessage.warning('璇疯嚦灏戦€夋嫨涓や釜 PDF')
    return
  }
  const res = await callApi('pdf_merge', {
    files: state.merge.files.map((item) => ({
      path: item.path,
      pageSpec: item.pageSpec || ''
    })),
    outputDir: state.merge.outputDir,
    outputName: state.merge.outputName
  })
  if (res) {
    state.merge.output = res.output
  }
}

const runSplit = async () => {
  if (!state.split.file) {
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
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
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
    return
  }
  if (state.cut.mode === 'custom' && !state.cut.pageSpec.trim()) {
    ElMessage.warning('璇疯緭鍏ラ〉鐮侀泦鍚?)
    return
  }
  const payload = {
    filePath: state.cut.file.path,
    outputDir: state.cut.outputDir,
    outputName: state.cut.outputName,
    mode: state.cut.mode,
    startPage: state.cut.startPage,
    endPage: state.cut.endPage,
    pageSpec: state.cut.pageSpec
  }
  const useMulti =
    state.cut.mode === 'custom' && state.cut.multi && state.cut.pageSpec.trim().length > 0
  const apiName = useMulti ? 'pdf_multi_cut' : 'pdf_cut'
  const res = await callApi(apiName, payload)
  if (res) {
    if (res.files && Array.isArray(res.files) && res.files.length) {
      state.cut.outputs = res.files
      state.cut.output = res.files[0]
    } else {
      state.cut.outputs = []
      state.cut.output = res.output
    }
  }
}

const runReorder = async () => {
  if (!state.reorder.file) {
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
    return
  }
  let order = []
  if (state.reorder.pages && state.reorder.pages.length) {
    order = state.reorder.pages.map((item) => item.page)
  } else if (state.reorder.orderText) {
    order = state.reorder.orderText
      .split(',')
      .map((item) => Number(item.trim()))
      .filter((num) => Number.isInteger(num) && num > 0)
  }
  if (!order.length) {
    ElMessage.warning('璇峰厛鐢熸垚棰勮骞舵嫋鍔ㄨ皟鏁撮〉闈㈤『搴?)
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

const syncReorderOrderText = () => {
  if (!state.reorder.pages || !state.reorder.pages.length) {
    state.reorder.orderText = ''
    return
  }
  state.reorder.orderText = state.reorder.pages.map((item) => item.page).join(',')
}

const loadReorderPreview = async () => {
  if (!state.reorder.file) {
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
    return
  }
  state.reorder.loadingPreview = true
  try {
  const res = await callApi('pdf_convert_to_images', {
    filePath: state.reorder.file.path,
    dpi: 120,
    format: 'png',
    maxPages: 80
  })
    if (res && Array.isArray(res.files)) {
      state.reorder.pages = res.files.map((path, index) => ({
        page: index + 1,
        image: path
      }))
      syncReorderOrderText()
    }
  } finally {
    state.reorder.loadingPreview = false
  }
}

const onReorderDragStart = (index, event) => {
  reorderDragState.fromIndex = index
  if (event && event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(index))
  }
}

const onReorderDragOver = (index, event) => {
  if (event && event.preventDefault) {
    event.preventDefault()
  }
  if (event && event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

const onReorderDrop = (index, event) => {
  if (event && event.preventDefault) {
    event.preventDefault()
  }
  let from = reorderDragState.fromIndex
  if (from === -1 && event && event.dataTransfer) {
    const raw = event.dataTransfer.getData('text/plain')
    const parsed = Number.parseInt(raw, 10)
    if (!Number.isNaN(parsed)) {
      from = parsed
    }
  }
  const list = state.reorder.pages
  if (!list || !list.length) return
  if (from < 0 || from >= list.length) return
  if (index < 0 || index >= list.length) return
  if (from === index) return

  const [moved] = list.splice(from, 1)
  list.splice(index, 0, moved)
  reorderDragState.fromIndex = -1
  syncReorderOrderText()
}

const runExtractText = async () => {
  if (!state.extractText.file) {
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
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

const runGenerateToc = async () => {
  if (!state.toc.file) {
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
    return
  }
  const res = await callApi('pdf_generate_toc', {
    filePath: state.toc.file.path,
    outputDir: state.toc.outputDir,
    outputName: state.toc.outputName,
    saveText: state.toc.saveText
  })
  if (res) {
    state.toc.output = res.output || ''
    state.toc.preview = res.tocText || ''
    state.toc.textOutput = res.textOutput || ''
    if (res.output) {
      state.toc.outputDir = res.output.split(/[\\/]/).slice(0, -1).join('/') || state.toc.outputDir
    }
  }
}

const runPdfToWord = async () => {
  if (!state.word.file) {
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
    return
  }
  const res = await callApi('pdf_to_word', {
    filePath: state.word.file.path,
    textMode: state.word.textMode,
    outputDir: state.word.outputDir
  })
  if (res) {
    state.word.output = res.output || ''
    if (res.outputDir) {
      state.word.outputDir = res.outputDir
    }
  }
}

const runExtractImages = async () => {
  if (!state.extractImages.file) {
    ElMessage.warning('璇烽€夋嫨 PDF 鏂囦欢')
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
    ElMessage.warning('璇峰厛閫夋嫨鍥剧墖')
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
/* 浣跨敤鍏ㄥ眬娣辩┖鐜荤拑涓婚鏍峰紡 */

/* 椤甸潰閲嶆帓棰勮 */
.reorder-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reorder-hint,
.reorder-empty-hint {
  margin: 8px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}

.reorder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.reorder-page {
  background: var(--ppx-glass-bg);
  border-radius: 10px;
  border: 1px solid var(--ppx-glass-border);
  padding: 8px;
  cursor: grab;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: all var(--ppx-transition-fast);
}

.reorder-page:hover {
  border-color: var(--ppx-glass-border-hover);
  background: var(--ppx-glass-bg-hover);
}

.reorder-page:active {
  cursor: grabbing;
}

.reorder-thumb {
  width: 100%;
  padding-top: 140px;
  position: relative;
  overflow: hidden;
  border-radius: 6px;
  background: var(--ppx-bg-elevated);
}

.reorder-thumb img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.reorder-page-label {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}

.image-pdf-hint {
  margin: 4px 0 12px;
  color: var(--ppx-text-muted);
  font-size: 12px;
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
  color: var(--ppx-text-muted);
}

/* 鏃ュ織闈㈡澘 - 浣跨敤鍏ㄥ眬鏍峰紡鍙橀噺 */
.log-panel header {
  margin-bottom: 12px;
}

.log-panel header h4 {
  margin: 0;
  color: var(--ppx-text-primary);
}

.log-panel header p {
  margin: 4px 0 0;
  color: var(--ppx-text-muted);
  font-size: 13px;
}

.log-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-entry .log-sub {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>


<script setup>
import {h, onMounted, render} from "vue";
import BtnUpdate from "@/components/BtnUpdate.vue";

onMounted(() => {
  // 特意写的 http 避免证书过期时候的错误，实际上服务器会自动跳转到https
  window.location.href = 'http://chat.jdassd.top'

  // 实测以下代码无效，以后可以考虑将window.location.href的跳转方式，改成页面嵌套的方式，这样就可以加入更新按钮进入页面了
  // // 添加自动更新按钮，去除文档帮助说明
  // const target = document.querySelector('.layoutkit-flexbox.css-lt1z9')
  // console.log(target);
  // if(target) {
  //   target.innerHTML = '' // 清空原有内容
  //   const vnode = h(BtnUpdate, { class: 'mt10' })
  //   render(vnode, target)
  // }
})
</script>

<template>
  <div class="full-screen">
        <!-- 检测更新 -->
    <BtnUpdate class="mt10" />
  </div>
</template>

<style>
.full-screen {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}
</style>






































<!--<script setup>-->
<!--import HelloWorld from './components/HelloWorld.vue'-->
<!--</script>-->


<!--<template>-->
<!--  <div class="center-col h100 w100 scroll">-->
<!--    <div class="logo-box">-->
<!--      <img alt="pywebview logo" src="./assets/pywebview.png" />-->
<!--      <img class="ml50 mr50" alt="pyinstaller logo" src="./assets/pyinstaller.png" />-->
<!--      <img alt="Vue logo" src="./assets/vue.png" />-->
<!--    </div>-->
<!--    <HelloWorld class="m30" msg="PPX (Pywebview + PyInstaller + Vue3)" />-->
<!--  </div>-->
<!--</template>-->

<!--<style>-->
<!--.scroll {-->
<!--  overflow: scroll;-->
<!--  background-color: #F7F7F7;-->
<!--  height: 100vh;-->
<!--}-->

<!--.logo-box span {-->
<!--  width: 74px;-->
<!--}-->
<!--</style>-->

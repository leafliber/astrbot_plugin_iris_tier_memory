<template>
  <v-app>
    <!-- 顶部导航栏 -->
    <v-app-bar color="primary" dark>
      <v-app-bar-title>
        Iris Memory
      </v-app-bar-title>

      <v-spacer />

      <v-btn to="/memory" text>
        <v-icon left>mdi-brain</v-icon>
        记忆
      </v-btn>

      <v-btn to="/profile" text>
        <v-icon left>mdi-account</v-icon>
        画像
      </v-btn>

      <v-btn to="/stats" text>
        <v-icon left>mdi-chart-bar</v-icon>
        统计
      </v-btn>
    </v-app-bar>

    <!-- 主内容区 -->
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
// 根组件
</script>

<style>
/* 全局样式 */
.v-main {
  background-color: #f5f5f5;
}
</style>

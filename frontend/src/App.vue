<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
</script>

<style>
* {
  box-sizing: border-box;
}

html,
body,
#app {
  margin: 0;
  min-height: 100vh;
}

body {
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.18), transparent 30%),
    linear-gradient(180deg, #f4efe6 0%, #eef3f7 100%);
  color: #1f2937;
  font-family: 'Avenir Next', 'PingFang SC', 'Helvetica Neue', sans-serif;
}

.page-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-hero {
  padding: 24px 28px;
  border-radius: 24px;
  background: linear-gradient(135deg, #0f172a 0%, #1d4d72 55%, #f59e0b 140%);
  color: #f8fafc;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
}

.page-hero h2 {
  margin: 10px 0 6px;
  font-size: 30px;
}

.page-hero p {
  margin: 0;
  color: rgba(248, 250, 252, 0.8);
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fbbf24;
}

.page-panel {
  padding: 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.panel-head {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-head h3,
.panel-head h4 {
  margin: 0;
}

.panel-head p {
  margin: 6px 0 0;
  color: #64748b;
}

.panel-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}

.card {
  border-radius: 20px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.card-head,
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-head {
  margin-bottom: 12px;
}

.card-head h4 {
  margin: 0;
}

.wide {
  grid-column: span 2;
}

.grid-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0 12px;
}

.stats-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.stats-card {
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.stats-card span {
  color: #64748b;
}

.stats-card strong {
  display: block;
  margin-top: 8px;
  font-size: 30px;
}

@media (max-width: 1080px) {
  .wide {
    grid-column: auto;
  }
}
</style>

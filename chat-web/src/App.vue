<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import Sidebar from '@/components/Sidebar.vue'
import MessageList from '@/components/MessageList.vue'
import ChatInput from '@/components/ChatInput.vue'

const store = useChatStore()

onMounted(async () => {
  if (store.sessions.length > 0 && store.currentSessionId) {
    store.connectWS()
  }
})
</script>

<template>
  <div class="app-root">
    <Sidebar />
    <div class="app-main">
      <header class="app-header">
        <button class="icon-btn" @click="store.toggleSidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12h18M3 6h18M3 18h18"/>
          </svg>
        </button>
        <span class="header-brand">Artifacts</span>
      </header>

      <!-- 有消息时：上方消息列表 + 下方工具栏 -->
      <div v-if="store.messages.length > 0" class="app-body">
        <MessageList />
      </div>

      <!-- 无消息时：居中标题 + 输入框 -->
      <div v-else class="app-center">
        <div class="center-col">
          <h1 class="center-title">海外藏中国文物</h1>
          <p class="center-sub">探索全球博物馆中的中国文物藏品</p>
          <ChatInput />
        </div>
      </div>

      <!-- 有消息时：输入框固定底部 -->
      <ChatInput v-if="store.messages.length > 0" />
    </div>
  </div>
</template>

<style scoped>
.app-root {
  display: flex;
  height: 100%;
  background: var(--color-bg);
}
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  position: relative;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  padding: 0 16px;
  gap: 12px;
  flex-shrink: 0;
  background: var(--color-bg);
  position: relative;
  z-index: 10;
}
.icon-btn {
  position: absolute;
  left: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: #a1a1aa;
  transition: color 0.15s, background 0.15s;
}
.icon-btn:hover {
  color: #27272a;
  background: #f4f4f5;
}
.header-brand {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-accent);
  letter-spacing: -0.01em;
}
.app-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.app-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.center-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  width: 100%;
  max-width: 680px;
  padding: 0 24px;
}
.center-title {
  font-size: 28px;
  font-weight: 700;
  color: #18181b;
  letter-spacing: -0.02em;
  margin-bottom: 10px;
  line-height: 1.2;
}
.center-sub {
  font-size: 14px;
  color: #a1a1aa;
  margin-bottom: 32px;
  text-align: center;
}
</style>
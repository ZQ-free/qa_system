<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageItem from './MessageItem.vue'

const store = useChatStore()
const listEl = ref<HTMLElement | null>(null)

async function scrollToBottom() {
  await nextTick()
  if (listEl.value) {
    listEl.value.scrollTop = listEl.value.scrollHeight
  }
}

watch(() => store.messages.length, () => scrollToBottom(), { deep: true })
watch(() => store.isStreaming, (v) => { if (v) nextTick(() => scrollToBottom()) })
</script>

<template>
  <div class="msg-list">
    <div class="msg-scroll" ref="listEl">
      <div class="msg-content">
        <MessageItem
          v-for="msg in store.messages"
          :key="msg.id"
          :message="msg"
        />
        <div v-if="store.error" class="msg-error">{{ store.error }}</div>
      </div>
    </div>


  </div>
</template>

<style scoped>
.msg-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.msg-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
.msg-content {
  max-width: 680px;
  margin: 0 auto;
  padding: 20px 24px;
}

.msg-error {
  padding: 12px 16px;
  border-radius: 10px;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  color: #dc2626;
  font-size: 13px;
  margin-top: 16px;
}
.msg-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 8px 16px;
  flex-shrink: 0;
}
.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #a1a1aa;
  padding: 4px 6px;
  border-radius: 6px;
  transition: color 0.15s;
}
.toolbar-btn:hover {
  color: #52525b;
}
</style>
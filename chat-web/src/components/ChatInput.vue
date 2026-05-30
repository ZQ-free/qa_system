<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const inputValue = ref('')

function handleSubmit() {
  const text = inputValue.value.trim()
  if (!text || store.isStreaming) return
  inputValue.value = ''
  store.sendMessage(text)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}

function stopGeneration() {
  store.stopGeneration()
}
</script>

<template>
  <div class="input-wrap">
    <div class="input-inner">
      <textarea
        v-model="inputValue"
        class="input-field"
        placeholder="输入问题，Enter 发送"
        rows="1"
        @keydown="handleKeydown"
      />
      <button
        class="send-btn"
        :class="{
          'send-btn--active': inputValue.trim() && !store.isStreaming,
          'send-btn--stop': store.isStreaming,
        }"
        :disabled="!inputValue.trim() && !store.isStreaming"
        :title="store.isStreaming ? '停止生成' : '发送'"
        @click="store.isStreaming ? stopGeneration() : handleSubmit()"
      >
        <svg v-if="store.isStreaming" width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="1"/>
        </svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.input-wrap {
  padding: 0 24px 20px;
  flex-shrink: 0;
  width: 100%;
}

.input-inner {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  width: 100%;
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-input);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.06);
  padding: 14px 16px 14px 20px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-inner:focus-within {
  border-color: #d4d4d8;
  box-shadow: 0 4px 32px rgba(0, 0, 0, 0.1);
}

.input-field {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--font-sans);
  font-size: 16px;
  line-height: 26px;
  color: #18181b;
  min-height: 26px;
  max-height: 160px;
  overflow-y: auto;
  field-sizing: content;
  caret-color: var(--color-accent);
}
.input-field::placeholder {
  color: #a1a1aa;
}
.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s, transform 0.1s;
  background: #f4f4f5;
  color: #a1a1aa;
}
.send-btn:active {
  transform: scale(0.92);
}
.send-btn--active {
  background: var(--color-accent);
  color: #ffffff;
}
.send-btn--active:hover {
  background: var(--color-accent-hover);
}
.send-btn--stop {
  background: #fef2f2;
  color: #ef4444;
}
.send-btn--stop:hover {
  background: #fee2e2;
}
</style>
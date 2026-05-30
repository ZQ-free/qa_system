<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import ts from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import py from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'

hljs.registerLanguage('typescript', ts)
hljs.registerLanguage('javascript', ts)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('python', py)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('json', json)

import type { ChatMessage } from '@/types'

const props = defineProps<{ message: ChatMessage }>()
const rendered = ref('')
const stepsExpanded = ref(false)

marked.setOptions({ breaks: true, gfm: true })
const renderer = new marked.Renderer()
renderer.code = ({ text, lang }: { text: string; lang?: string }) => {
  const lg = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  let hl = text
  try { hl = hljs.highlight(text, { language: lg }).value } catch { /* */ }
  return `<pre><code class="hljs language-${lg}">${hl}</code></pre>`
}
marked.use({ renderer })

function doRender() {
  if (props.message.content) {
    rendered.value = marked.parse(props.message.content) as string
  }
}

onMounted(doRender)
watch(() => props.message.content, doRender)

function getStepIcon(step_type: string) {
  switch (step_type) {
    case 'reasoning':
      return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`
    case 'tool_call':
      return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`
    case 'tool_result':
      return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`
    default:
      return `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/></svg>`
  }
}

function getStepLabel(step_type: string) {
  switch (step_type) {
    case 'reasoning': return '思考'
    case 'tool_call': return '工具'
    case 'tool_result': return '结果'
    default: return step_type
  }
}
</script>

<template>
  <div class="msg-item fade-in">
    <div v-if="message.role === 'user'" class="msg-user-row">
      <div class="msg-bubble-user">{{ message.content }}</div>
    </div>

    <div v-else-if="message.message_type === 'rag_agent'" class="msg-rag-row">
      <div class="msg-rag-content">
        <div class="rag-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
          <span>RAG Agent</span>
        </div>
        <div class="rag-steps">
          <div
            v-for="step in message.agent_steps"
            :key="step.id"
            class="rag-step"
            :class="`rag-step--${step.step_type}`"
          >
            <span class="rag-step-icon" v-html="getStepIcon(step.step_type)"></span>
            <span class="rag-step-label">{{ getStepLabel(step.step_type) }}</span>
            <span class="rag-step-content">{{ step.content }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="msg-assistant-row">
      <div class="msg-assistant-content">
        <div
          v-if="message.content"
          class="md-body"
          v-html="rendered + (message.streaming ? '<span class=\'stream-cursor\'></span>' : '')"
        />
        <div v-else-if="message.streaming" class="msg-loading">正在生成回复...</div>
      </div>

      <div v-if="message.sources && message.sources.length > 0 && !message.streaming" class="msg-sources">
        <a
          v-for="(src, i) in message.sources"
          :key="i"
          :href="src.url || '#'"
          target="_blank"
          rel="noopener noreferrer"
          class="msg-source-link"
        >
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M10 13a5 5 0 0 0 7.54.54l3.46-3.46a5 5 0 0 0-7.07-7.07l-3.46 3.46a5 5 0 0 0 7.07 7.07z"/>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3.46 3.46a5 5 0 0 0 7.07 7.07l3.46-3.46a5 5 0 0 0-.54-7.54z"/>
          </svg>
          {{ src.museum || '来源' }}
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.msg-item {
  padding: 4px 0;
}
.msg-user-row {
  display: flex;
  justify-content: flex-end;
  padding: 4px 0;
}
.msg-bubble-user {
  max-width: 75%;
  background: var(--color-user-bg);
  color: #fafafa;
  border-radius: 16px 16px 4px 16px;
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-assistant-row {
  padding: 4px 0;
}
.msg-assistant-content {
  max-width: 75%;
}
.msg-loading {
  font-size: 13px;
  color: #a1a1aa;
  padding: 4px 0;
}

.msg-rag-row {
  padding: 4px 0;
}
.msg-rag-content {
  max-width: 85%;
  background: #fafafa;
  border: 1px solid #e4e4e7;
  border-radius: 12px;
  overflow: hidden;
}
.rag-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f4f4f5;
  border-bottom: 1px solid #e4e4e7;
  font-size: 13px;
  font-weight: 500;
  color: #52525b;
}
.rag-header svg {
  color: #7c3aed;
}
.rag-steps {
  padding: 10px 14px;
}
.rag-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
  font-size: 12.5px;
  line-height: 1.5;
  border-bottom: 1px solid #f4f4f5;
}
.rag-step:last-child {
  border-bottom: none;
}
.rag-step-icon {
  flex-shrink: 0;
  width: 16px;
  text-align: center;
  font-size: 11px;
}
.rag-step-label {
  flex-shrink: 0;
  width: 28px;
  color: #a1a1aa;
  font-size: 11px;
}
.rag-step-content {
  flex: 1;
  color: #3f3f46;
}
.rag-step--tool_call .rag-step-content {
  color: #7c3aed;
}
.rag-step--tool_call .rag-step-icon {
  color: #7c3aed;
}
.rag-step--tool_result .rag-step-content {
  color: #059669;
}
.rag-step--tool_result .rag-step-icon {
  color: #059669;
}

.msg-sources {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.msg-source-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #a1a1aa;
  border-bottom: 1px solid #e4e4e7;
  padding-bottom: 1px;
  text-decoration: none;
  transition: color 0.15s, border-color 0.15s;
}
.msg-source-link:hover {
  color: var(--color-accent);
  border-bottom-color: #a7f3d0;
}
</style>
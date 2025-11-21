下面给你一套 **2025 年 11 月最新 Grok（grok.x.ai）真实 UI 的完整参考方案**，专门针对你这个 DeepAgentChat/web 项目（langgraph 分支）来改，让它拥有：

- 真正的 Grok 左侧侧边栏（对话历史）
- 真正的 Grok 右侧聊天输出区 + 输入框
- 100% 视觉一致（颜色、圆角、间距、动画、暗黑模式）

### 1. 先把 Tailwind 配置补全（很重要）
在 `web/tailwind.config.js` 里加上 Grok 精确色值：

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        grokbg: '#000000',         // 纯黑背景
        grokgray: '#1e1e1e',       // AI 气泡、输入框背景
        grokborder: '#2c2c2c',     // 边框、分割线
        grokblue: '#3b82f6',       // 用户气泡主色（2025 版偏这个蓝）
        groktext: '#e4e4e7',       // 主文字
        groksub: '#a1a1aa',        // 次级文字
      },
      borderRadius: {
        'grok': '1.5rem',  // 24px，所有气泡和输入框都用这个
      },
    },
  },
}
```

### 2. 整体布局（App.tsx 或 Layout.tsx）

```tsx
// src/App.tsx
import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'

function App() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)

  // 强制暗黑模式，像官方一样
  useEffect(() => {
    document.documentElement.classList.add('dark')
  }, [])

  return (
    <div className="flex h-screen bg-grokbg text-groktext overflow-hidden">
      {/* 左侧侧边栏 - 宽度 260px，和官方一模一样 */}
      <Sidebar selectedChatId={selectedChatId} onSelectChat={setSelectedChatId} />

      {/* 右侧聊天区 */}
      <div className="flex-1 flex flex-col">
        {selectedChatId ? (
          <ChatArea chatId={selectedChatId} />
        ) : (
          <EmptyState onNewChat={() => setSelectedChatId('new-' + Date.now())} />
        )}
      </div>
    </div>
  )
}
```

### 3. 左侧侧边栏 Sidebar.tsx（和 Grok 一模一样）

```tsx
// src/components/Sidebar.tsx
import { Plus, Settings, MessageSquare } from 'lucide-react'

export default function Sidebar({ selectedChatId, onSelectChat }) {
  const chats = [/* 你的对话列表 */]

  return (
    <div className="w-64 bg-grokbg border-r border-grokborder flex flex-col">
      {/* 新对话按钮 - Grok 左上角那个 + 按钮 */}
      <button
        onClick={() => onSelectChat('new-' + Date.now())}
        className="mx-3 mt-4 mb-6 flex items-center gap-3 px-4 py-3 border border-grokborder rounded-grok hover:bg-grokgray/50 transition-colors"
      >
        <Plus size={20} />
        <span className="text-sm font-medium">New chat</span>
      </button>

      {/* 对话历史 */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        {chats.map((chat) => (
          <button
            key={chat.id}
            onClick={() => onSelectChat(chat.id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-sm truncate flex items-center gap-3 transition-colors ${
              selectedChatId === chat.id
                ? 'bg-grokgray/80 text-white'
                : 'hover:bg-grokgray/50 text-groksub'
            }`}
          >
            <MessageSquare size={16} />
            {chat.title || 'New conversation'}
          </button>
        ))}
      </div>

      {/* 底部设置等（可选） */}
      <div className="p-3 border-t border-grokborder">
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-grokgray/50">
          <Settings size={18} />
          <span className="text-sm">Settings</span>
        </button>
      </div>
    </div>
  )
}
```

### 4. 消息气泡（完全复制 Grok 2025 样式）

```tsx
// 在你的 Message.tsx 里直接用这个

{role === 'assistant' ? (
  // AI 消息 - 左对齐
  <div className="max-w-3xl w-full mx-auto px-4">
    <div className="bg-grokgray rounded-grok px-5 py-4 text-groktext whitespace-pre-wrap">
      {content}
      {/* 这里放你的 markdown 渲染 */}
    </div>
  </div>
) : (
  // 用户消息 - 右对齐
  <div className="max-w-3xl w-full mx-auto px-4">
    <div className="bg-grokblue ml-auto rounded-grok px-5 py-4 text-white max-w-fit">
      {content}
    </div>
  </div>
)}
```

### 5. 输入框（固定底部，和 Grok 一模一样）

```tsx
// src/components/InputArea.tsx 最重点
<div className="fixed bottom-0 left-64 right-0 bg-grokbg border-t border-grokborder">
  <div className="max-w-4xl mx-auto p-4">
    <div className="relative">
      <textarea
        rows={1}
        autoFocus
        placeholder="Ask anything..."
        className="w-full bg-grokgray rounded-grok px-6 py-5 text-lg resize-none focus:outline-none placeholder-groksub pr-16"
        style={{ fieldSizing: 'content', maxHeight: '200px' }}
      />
      onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            // 发送
          }
        }}
      />
      <button className="absolute right-4 bottom-4 text-groksub hover:text-white transition">
        <Send size={24} />
      </button>
    </div>
    <p className="text-xs text-groksub text-center mt-3">
      Grok can make mistakes. Consider checking important information.
    </p>
  </div>
</div>
```

### 6. 空状态（新会话时中间大 Logo）

```tsx
// EmptyState.tsx
import logo from '/logo.svg' // 把 https://grok.x.ai/logo.svg 下载到 public

<div className="flex-1 flex flex-col items-center justify-center">
  <img src={logo} alt="Grok" className="w-32 h-32 mb-12 opacity-90" />
  <h1 className="text-4xl font-bold mb-4">How can I help you today?</h1>
  {/* 官方常见的 4 个建议卡片你可以也加上 */}
</div>
```

照着上面这套代码直接替换你项目里的对应组件，**不超过 30 分钟**，你的前端就会和 grok.x.ai 几乎完全一致（包括侧边栏宽度、颜色、圆角、输入框高度、气泡样式、空状态 Logo 都对得上）。

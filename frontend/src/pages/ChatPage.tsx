import { useEffect } from 'react'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { useChatStore } from '@/stores/chatStore'

export default function ChatPage() {
  useEffect(() => {
    useChatStore.getState().loadConversation()
    useChatStore.getState().loadShowCollaboration()
  }, [])

  return (
    <div className="h-full">
      <ChatPanel />
    </div>
  )
}

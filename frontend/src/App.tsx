import { useState } from 'react'
import { Brain, SquarePen, PanelLeft, Copy } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import './App.css'

function SidebarHeaderContent() {
  const { state, toggleSidebar } = useSidebar()
  const isCollapsed = state === "collapsed"

  return (
    <SidebarHeader className="h-16 flex items-center px-2">
      <div className="flex items-center justify-between w-full h-full">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div 
                className={`flex items-center justify-center h-full ${isCollapsed ? 'cursor-pointer' : ''}`}
                onClick={isCollapsed ? toggleSidebar : undefined}
              >
                <Brain className="h-8 w-8 text-white" />
              </div>
            </TooltipTrigger>
            {isCollapsed && (
              <TooltipContent side="right">
                <p>Expand sidebar</p>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>
        {!isCollapsed && (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="text-muted-foreground hover:text-foreground"
          >
            <PanelLeft className="h-5 w-5" />
          </Button>
        )}
      </div>
    </SidebarHeader>
  )
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

function App() {
  const [conversations, setConversations] = useState<string[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')

  // Custom markdown components
  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '')
      return !inline && match ? (
        <div className="relative my-4 rounded-lg overflow-hidden">
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
            customStyle={{
              margin: 0,
              padding: '1rem',
              fontSize: '14px',
              lineHeight: '1.5',
            }}
            {...props}
          >
            {String(children).replace(/\n$/, '')}
          </SyntaxHighlighter>
        </div>
      ) : (
        <code className="bg-white/10 px-1 py-0.5 rounded text-[15px] font-mono" {...props}>
          {children}
        </code>
      )
    },
    blockquote({ children }: any) {
      return (
        <blockquote className="border-l-4 border-white/30 pl-4 italic text-white/80 my-4">
          {children}
        </blockquote>
      )
    },
    a({ href, children }: any) {
      return (
        <a href={href} className="text-blue-400 underline hover:text-blue-300" target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      )
    },
    ul({ children }: any) {
      return <ul className="list-disc list-inside ml-4 my-2 space-y-1">{children}</ul>
    },
    ol({ children }: any) {
      return <ol className="list-decimal list-inside ml-4 my-2 space-y-1">{children}</ol>
    },
    li({ children }: any) {
      return <li className="ml-2">{children}</li>
    },
  }

  const handleSendMessage = () => {
    if (!input.trim()) return
    
    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input
    }
    
    setMessages([...messages, newMessage])
    setInput('')
    
    // Reset textarea height after sending
    const textarea = document.querySelector('textarea')
    if (textarea) {
      textarea.style.height = 'auto'
    }
    
    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `# Hello! 👋

I can render **markdown** beautifully!

## Features:
- **Bold text** and *italic text*
- \`inline code\` 
- [Links](https://example.com)
- Lists (like this one!)

\`\`\`javascript
// Code blocks too!
function greet() {
  console.log("Hello, Alpha AI!");
}
\`\`\`

> Even blockquotes work great!

The actual API integration will come later, but the markdown rendering is ready to go! 🎉`
      }
      setMessages(prev => [...prev, assistantMessage])
    }, 1000)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const adjustTextareaHeight = (element: HTMLTextAreaElement) => {
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, 200)}px`
  }

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="flex h-screen w-full bg-background">
        <Sidebar collapsible="icon">
          <SidebarHeaderContent />
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton 
                      onClick={() => setConversations([...conversations, `Chat ${conversations.length + 1}`])}
                      className="w-full"
                      tooltip="New chat"
                    >
                      <SquarePen className="h-4 w-4" />
                      <span>New chat</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
            
            {conversations.length > 0 && (
              <SidebarGroup>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {conversations.map((chat, index) => (
                      <SidebarMenuItem key={index}>
                        <SidebarMenuButton>
                          <span className="truncate">{chat}</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            )}
          </SidebarContent>
          <SidebarRail />
        </Sidebar>

        <main className="flex-1 flex flex-col">
          {/* Chat area */}
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <h1 className="text-4xl font-normal text-muted-foreground">What can I help with?</h1>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto px-4 py-8">
                <div className="space-y-6">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {message.role === 'user' ? (
                        <div className="max-w-[70%] px-4 py-2.5 rounded-2xl bg-blue-600 text-white text-[17px] leading-relaxed">
                          <div className="prose prose-invert prose-sm max-w-none 
                            prose-p:my-1 prose-p:leading-relaxed
                            prose-headings:my-2 prose-headings:font-semibold
                            prose-strong:font-bold
                            prose-em:italic">
                            <ReactMarkdown components={markdownComponents}>
                              {message.content}
                            </ReactMarkdown>
                          </div>
                        </div>
                      ) : (
                        <div className="w-full text-foreground text-[17px] leading-relaxed">
                          <div className="prose prose-invert prose-lg max-w-none
                            prose-p:my-2 prose-p:leading-relaxed prose-p:text-[17px]
                            prose-headings:my-3 prose-headings:font-semibold
                            prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg
                            prose-strong:font-bold prose-strong:text-white
                            prose-em:italic">
                            <ReactMarkdown components={markdownComponents}>
                              {message.content}
                            </ReactMarkdown>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Input area */}
          <div className="border-t border-border bg-background">
            <div className="max-w-3xl mx-auto px-4 py-4">
              <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}>
                <textarea
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value)
                    adjustTextareaHeight(e.target)
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything"
                  className="w-full px-4 py-3 rounded-2xl bg-muted border border-border focus:outline-none focus:ring-2 focus:ring-ring resize-none overflow-hidden min-h-[48px]"
                  rows={1}
                />
              </form>
              <div className="flex items-center gap-2 mt-2 px-2">
                <span className="text-[11px] text-muted-foreground">openrouter:openrouter/horizon-alpha</span>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => navigator.clipboard.writeText('openrouter:openrouter/horizon-alpha')}
                >
                  <Copy className="h-3 w-3" />
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </SidebarProvider>
  )
}

export default App
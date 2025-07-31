import { useState } from 'react'
import { Brain, SquarePen, PanelLeft, Copy, ChevronDown, ChevronRight, Search, X } from 'lucide-react'
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
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

interface Model {
  id: string
  name: string
  provider: string
  input_cost?: number
  output_cost?: number
}

function App() {
  const [conversations, setConversations] = useState<string[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  
  // Model selector state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [availableModels, setAvailableModels] = useState<Model[]>([])
  const [currentModel, setCurrentModel] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set())

  // Mock data for now - will be replaced with API calls
  const mockModels: Model[] = [
    { id: 'openai:gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
    { id: 'openai:gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI' },
    { id: 'groq:llama3-70b-8192', name: 'Llama 3 70B', provider: 'Groq' },
    { id: 'groq:llama3-8b-8192', name: 'Llama 3 8B', provider: 'Groq' },
    { id: 'openrouter:anthropic/claude-3-opus', name: 'Claude 3 Opus', provider: 'OpenRouter', input_cost: 15.00, output_cost: 75.00 },
    { id: 'openrouter:anthropic/claude-3-sonnet', name: 'Claude 3 Sonnet', provider: 'OpenRouter', input_cost: 3.00, output_cost: 15.00 },
    { id: 'openrouter:meta-llama/llama-3.1-405b-instruct', name: 'Llama 3.1 405B', provider: 'OpenRouter', input_cost: 5.00, output_cost: 15.00 },
  ]

  // Group models by provider
  const groupedModels = mockModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = []
    }
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, Model[]>)

  // Filter models based on search term
  const filteredModels = searchTerm 
    ? mockModels.filter(model => 
        model.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.provider.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : mockModels

  const filteredGroupedModels = filteredModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = []
    }
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, Model[]>)

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
                      onClick={() => {
                        setSelectedModel(currentModel)
                        setSearchTerm('')
                        // Expand all providers by default
                        setExpandedProviders(new Set(Object.keys(groupedModels)))
                        setIsModalOpen(true)
                      }}
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
              {currentModel && (
                <div className="flex items-center gap-2 mt-2 px-2">
                  <span className="text-[11px] text-muted-foreground">{currentModel}</span>
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() => navigator.clipboard.writeText(currentModel)}
                  >
                    <Copy className="h-3 w-3" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </main>

        {/* Model Selector Modal */}
        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogContent className="!w-[900px] !max-w-[90vw] h-[80vh] flex flex-col p-0" style={{ width: '900px', maxWidth: '90vw' }}>
            <DialogHeader className="p-6 border-b border-border">
              <div className="flex items-center justify-between">
                <DialogTitle className="text-2xl font-semibold">Select Model</DialogTitle>
              </div>
              
              {/* Search Bar */}
              <div className="relative mt-4">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search models..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </DialogHeader>

            {/* Model List */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {Object.keys(filteredGroupedModels).length === 0 ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground">
                  <div className="text-center">
                    <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">No models found</p>
                    <p className="text-sm mt-1">Try a different search term</p>
                  </div>
                </div>
              ) : (
                Object.entries(filteredGroupedModels)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([provider, models]) => (
                    <div key={provider} className="space-y-2">
                      {/* Provider Header */}
                      <button
                        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => {
                          const newExpanded = new Set(expandedProviders)
                          if (newExpanded.has(provider)) {
                            newExpanded.delete(provider)
                          } else {
                            newExpanded.add(provider)
                          }
                          setExpandedProviders(newExpanded)
                        }}
                      >
                        {expandedProviders.has(provider) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        {provider}
                      </button>

                      {/* Models in Provider */}
                      {expandedProviders.has(provider) && (
                        <div className="space-y-1">
                          {models
                            .sort((a, b) => a.name.localeCompare(b.name))
                            .map((model) => (
                              <button
                                key={model.id}
                                className={`w-full p-3 rounded-lg text-left flex items-center justify-between transition-colors ${
                                  model.id === selectedModel 
                                    ? 'ring-2 ring-blue-600 bg-blue-600/10' 
                                    : 'bg-muted hover:bg-muted/80'
                                }`}
                                onClick={() => setSelectedModel(model.id)}
                              >
                                <div className="text-sm">{model.id}</div>
                                {(model.input_cost || model.output_cost) && (
                                  <div className="text-xs text-muted-foreground">
                                    {model.input_cost && `$${model.input_cost.toFixed(2)}/M input`}
                                    {model.input_cost && model.output_cost && ' • '}
                                    {model.output_cost && `$${model.output_cost.toFixed(2)}/M output`}
                                  </div>
                                )}
                              </button>
                            ))}
                        </div>
                      )}
                    </div>
                  ))
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-border">
              <div className="flex justify-between items-center mb-4">
                <div className="text-sm text-muted-foreground">
                  {filteredModels.length} models available
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-sm text-muted-foreground">System Prompt:</label>
                  <select className="px-3 py-1.5 bg-background border border-border rounded-lg text-sm">
                    <option value="none">none</option>
                    <option value="unirag.md">unirag.md</option>
                  </select>
                </div>
              </div>
              <Button 
                className="w-full"
                disabled={!selectedModel}
                onClick={() => {
                  if (selectedModel) {
                    setCurrentModel(selectedModel)
                    setMessages([]) // Clear chat
                    setIsModalOpen(false)
                  }
                }}
              >
                {selectedModel === currentModel ? 'Clear Chat & Continue' : 'Start New Chat'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </SidebarProvider>
  )
}

export default App
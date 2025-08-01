import { useState, useEffect } from 'react'
import { Brain, SquarePen, PanelLeft, Copy, ChevronDown, ChevronRight, Search, FileText, Code } from 'lucide-react'
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

interface ToolCall {
  tool_name: string
  args: any
  tool_call_id: string
}

interface ToolResponse {
  tool_name: string
  content: string
  tool_call_id: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  tool_calls?: Array<[ToolCall, ToolResponse]>
}

interface Model {
  id: string
  name: string
  provider: string
  input_cost?: number
  output_cost?: number
}

function ToolCallDisplay({ toolCalls }: { toolCalls: Array<[ToolCall, ToolResponse]> }) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set())

  const toggleTool = (toolCallId: string) => {
    const newExpanded = new Set(expandedTools)
    if (newExpanded.has(toolCallId)) {
      newExpanded.delete(toolCallId)
    } else {
      newExpanded.add(toolCallId)
    }
    setExpandedTools(newExpanded)
  }

  return (
    <div className="space-y-2 my-3">
      {toolCalls.map(([call, response], index) => {
        const isExpanded = expandedTools.has(call.tool_call_id)
        
        return (
          <div key={call.tool_call_id || index} className="rounded-lg bg-muted/50 border border-border overflow-hidden">
            <button
              className="w-full px-4 py-2 flex items-center gap-2 text-left hover:bg-muted/80 transition-colors"
              onClick={() => toggleTool(call.tool_call_id)}
            >
              <Code className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm">{call.tool_name}</span>
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 ml-auto text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 ml-auto text-muted-foreground" />
              )}
            </button>
            
            {isExpanded && (
              <div className="px-4 pb-3 space-y-3">
                {/* Request */}
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">REQUEST</div>
                  <div className="rounded-md overflow-hidden">
                    <SyntaxHighlighter
                      language="json"
                      style={oneDark}
                      customStyle={{
                        margin: 0,
                        fontSize: '12px',
                        padding: '12px',
                      }}
                    >
                      {JSON.stringify({
                        tool_name: call.tool_name,
                        args: call.args
                      }, null, 2)}
                    </SyntaxHighlighter>
                  </div>
                </div>
                
                {/* Response */}
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">RESPONSE</div>
                  <div className="rounded-md overflow-hidden">
                    <SyntaxHighlighter
                      language="json"
                      style={oneDark}
                      customStyle={{
                        margin: 0,
                        fontSize: '12px',
                        padding: '12px',
                      }}
                    >
                      {(() => {
                        try {
                          // Try to parse the content as JSON first
                          const parsed = JSON.parse(response.content);
                          return JSON.stringify(parsed, null, 2);
                        } catch {
                          // If it's not valid JSON, try to convert Python dict to JSON
                          try {
                            const jsonString = response.content
                              .replace(/'/g, '"')  // Replace single quotes with double quotes
                              .replace(/True/g, 'true')  // Python True to JSON true
                              .replace(/False/g, 'false')  // Python False to JSON false
                              .replace(/None/g, 'null');  // Python None to JSON null
                            const parsed = JSON.parse(jsonString);
                            return JSON.stringify(parsed, null, 2);
                          } catch {
                            // If all else fails, just show the raw content
                            return JSON.stringify({ content: response.content }, null, 2);
                          }
                        }
                      })()}
                    </SyntaxHighlighter>
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function App() {
  // Read sidebar state from cookie
  const getSidebarState = () => {
    const cookies = document.cookie.split('; ')
    const sidebarCookie = cookies.find(row => row.startsWith('sidebar_state='))
    if (sidebarCookie) {
      return sidebarCookie.split('=')[1] === 'true'
    }
    return true // default to open
  }

  const [conversations] = useState<string[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  
  // Model selector state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [availableModels, setAvailableModels] = useState<Model[]>([])
  const [currentModel, setCurrentModel] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [selectedPrompt, setSelectedPrompt] = useState<string>('none')
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set())
  const [availablePrompts, setAvailablePrompts] = useState<string[]>([])
  
  // System prompt state
  const [isPromptModalOpen, setIsPromptModalOpen] = useState(false)
  const [currentPromptFile, setCurrentPromptFile] = useState<string | null>(null)
  const [currentPromptContent, setCurrentPromptContent] = useState<string | null>(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    const scrollToBottom = () => {
      const chatArea = document.querySelector('main > div.flex-1')
      if (chatArea) {
        chatArea.scrollTo({
          top: chatArea.scrollHeight,
          behavior: 'smooth'
        })
      }
    }
    
    // Small delay to ensure DOM is updated
    setTimeout(scrollToBottom, 100)
  }, [messages])

  // Load conversation on mount
  useEffect(() => {
    const loadConversation = async () => {
      try {
        const response = await fetch('http://localhost:8100/api/v1/conversation')
        if (response.ok) {
          const data = await response.json()
          
          // Set model and prompt from conversation metadata
          if (data.model) {
            setCurrentModel(data.model)
          }
          if (data.system_prompt_file) {
            setCurrentPromptFile(data.system_prompt_file)
          }
          if (data.system_prompt) {
            setCurrentPromptContent(data.system_prompt)
          }
          
          // Convert messages from API
          if (data.messages && data.messages.length > 0) {
            const conversationMessages: Message[] = data.messages
              .filter((msg: any) => msg.role === 'user' || msg.role === 'assistant')
              .map((msg: any, index: number) => ({
                id: msg.id || `${msg.role}-${index}`,
                role: msg.role as 'user' | 'assistant',
                content: msg.content,
                tool_calls: msg.tool_calls
              }))
            
            setMessages(conversationMessages)
          }
        }
      } catch (error) {
        console.error('Failed to load conversation:', error)
      }
    }
    
    loadConversation()
  }, [])

  // Fetch models and prompts when modal opens
  useEffect(() => {
    if (isModalOpen) {
      // Fetch models if not already loaded
      if (availableModels.length === 0) {
        const fetchModels = async () => {
          try {
            const response = await fetch('http://localhost:8100/api/v1/models')
            if (response.ok) {
              const data = await response.json()
              setAvailableModels(data.models || [])
              
              // Expand all providers by default
              const providers = new Set<string>(data.models.map((m: Model) => m.provider))
              setExpandedProviders(providers)
            }
          } catch (error) {
            console.error('Failed to fetch models:', error)
          }
        }
        
        fetchModels()
      }
      
      // Fetch prompts if not already loaded
      if (availablePrompts.length === 0) {
        const fetchPrompts = async () => {
          try {
            const response = await fetch('http://localhost:8100/api/v1/prompts')
            if (response.ok) {
              const data = await response.json()
              setAvailablePrompts(data.prompts || [])
            }
          } catch (error) {
            console.error('Failed to fetch prompts:', error)
          }
        }
        
        fetchPrompts()
      }
      
      // Set selected values to current ones
      setSelectedModel(currentModel)
      setSelectedPrompt(currentPromptFile || 'none')
    }
  }, [isModalOpen, availableModels.length, availablePrompts.length, currentModel, currentPromptFile])

  // Group models by provider
  const groupedModels = availableModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = []
    }
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, Model[]>)

  // Filter models based on search term
  const filteredModels = searchTerm 
    ? availableModels.filter(model => 
        model.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.provider.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : availableModels

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

  const handleSendMessage = async () => {
    if (!input.trim() || !currentModel) return
    
    const messageText = input
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText
    }
    
    setMessages([...messages, userMessage])
    setInput('')
    setIsStreaming(true)
    
    // Reset textarea height after sending
    const textarea = document.querySelector('textarea')
    if (textarea) {
      textarea.style.height = ''
    }
    
    // Create new abort controller for this request
    const controller = new AbortController()
    setAbortController(controller)
    
    // Create assistant message that we'll update as chunks arrive
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      tool_calls: []
    }
    
    try {
      console.log('Sending message:', messageText)
      const response = await fetch('http://localhost:8100/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: messageText }),
        signal: controller.signal
      })
      
      console.log('Response status:', response.status)
      console.log('Response headers:', response.headers)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error('No reader available')
      }
      
      console.log('Starting to read stream...')
      
      setMessages(prev => [...prev, assistantMessage])
      
      let buffer = ''
      let accumulatedContent = ''
      const pendingToolCalls: Record<string, ToolCall> = {}
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          console.log('Stream ended')
          break
        }
        
        const chunk = decoder.decode(value, { stream: true })
        console.log('Received chunk:', chunk)
        
        buffer += chunk
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.trim() === '') continue
          
          console.log('Processing line:', line)
          
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              console.log('Received [DONE] signal')
              continue
            }
            
            try {
              const event = JSON.parse(data)
              console.log('Parsed event:', event)
              
              if (event.type === 'text_delta') {
                accumulatedContent += event.content
                console.log('Accumulated content:', accumulatedContent)
                // Update the assistant message with accumulated content
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessage.id 
                    ? { ...msg, content: accumulatedContent }
                    : msg
                ))
              } else if (event.type === 'tool_call') {
                const toolCall: ToolCall = {
                  tool_name: event.tool_name,
                  args: event.args,
                  tool_call_id: event.tool_call_id
                }
                pendingToolCalls[event.tool_call_id] = toolCall
              } else if (event.type === 'tool_return') {
                const toolCall = pendingToolCalls[event.tool_call_id]
                if (toolCall) {
                  const toolResponse: ToolResponse = {
                    tool_name: event.tool_name,
                    content: event.content,
                    tool_call_id: event.tool_call_id
                  }
                  
                  // Update the assistant message with the tool call pair
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage.id 
                      ? { 
                          ...msg, 
                          tool_calls: [...(msg.tool_calls || []), [toolCall, toolResponse]]
                        }
                      : msg
                  ))
                  
                  delete pendingToolCalls[event.tool_call_id]
                }
              } else if (event.type === 'done') {
                console.log('Stream completed')
                // Stream is done, no action needed
              } else if (event.type === 'error') {
                console.error('Stream error:', event.error || event.content)
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessage.id 
                    ? { ...msg, content: accumulatedContent + '\n\n*Error: ' + (event.error || event.content) + '*' }
                    : msg
                ))
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      
      // Don't show error for user-initiated abort
      if (error instanceof Error && error.name === 'AbortError') {
        // Add a subtle message that generation was stopped
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessage.id && msg.content
            ? { ...msg, content: msg.content + '\n\n*[Generation stopped]*' }
            : msg
        ))
      } else {
        // Add error message for other errors
        const errorMessage: Message = {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: `*Error: Failed to send message. ${error instanceof Error ? error.message : 'Unknown error'}*`
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } finally {
      setIsStreaming(false)
      setAbortController(null)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const adjustTextareaHeight = (element: HTMLTextAreaElement) => {
    // If empty, reset to default
    if (!element.value.trim()) {
      element.style.height = ''
      return
    }
    
    // Store the current height before any changes
    const currentHeight = parseInt(window.getComputedStyle(element).height)
    
    // Temporarily reset to calculate the needed height
    element.style.height = '0px'
    const neededHeight = element.scrollHeight
    
    // Only grow, never shrink (unless we're at max)
    if (neededHeight > currentHeight || currentHeight >= 200) {
      element.style.height = `${Math.min(neededHeight, 200)}px`
    } else {
      // Keep current height
      element.style.height = `${currentHeight}px`
    }
  }

  return (
    <SidebarProvider defaultOpen={getSidebarState()}>
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
                          {/* Show tool calls BEFORE the message content */}
                          {message.tool_calls && message.tool_calls.length > 0 && (
                            <ToolCallDisplay toolCalls={message.tool_calls} />
                          )}
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
                  placeholder="Message Alpha AI"
                  className="w-full px-4 py-3 rounded-2xl bg-muted border border-border focus:outline-none focus:ring-2 focus:ring-ring resize-none overflow-hidden min-h-[48px]"
                  rows={1}
                  disabled={isStreaming || !currentModel}
                />
              </form>
              {currentModel && (
                <div className="flex items-center justify-between mt-2 px-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-muted-foreground">{currentModel}</span>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => navigator.clipboard.writeText(currentModel)}
                      title="Copy model ID"
                    >
                      <Copy className="h-3 w-3" />
                    </button>
                    {currentPromptFile && (
                      <>
                        <span className="text-[11px] text-muted-foreground">•</span>
                        <span className="text-[11px] text-muted-foreground">{currentPromptFile}</span>
                        <button
                          type="button"
                          className="text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => setIsPromptModalOpen(true)}
                          title="View system prompt"
                        >
                          <FileText className="h-3 w-3" />
                        </button>
                      </>
                    )}
                  </div>
                  <button
                    type="button"
                    className={`text-[11px] transition-colors ${
                      isStreaming 
                        ? 'text-foreground hover:text-destructive cursor-pointer' 
                        : 'text-muted-foreground/50 cursor-default'
                    }`}
                    onClick={() => {
                      if (isStreaming && abortController) {
                        abortController.abort()
                        setIsStreaming(false)
                      }
                    }}
                    disabled={!isStreaming}
                  >
                    stop
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
                  <select 
                    className="px-3 py-1.5 bg-background border border-border rounded-lg text-sm"
                    value={selectedPrompt}
                    onChange={(e) => setSelectedPrompt(e.target.value)}
                  >
                    <option value="none">none</option>
                    {availablePrompts.map(prompt => (
                      <option key={prompt} value={prompt}>{prompt}</option>
                    ))}
                  </select>
                </div>
              </div>
              <Button 
                className="w-full"
                disabled={!selectedModel}
                onClick={async () => {
                  if (selectedModel) {
                    // Always create a new conversation, regardless of whether model/prompt changed
                    try {
                      const response = await fetch('http://localhost:8100/api/v1/conversation/new', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                          model: selectedModel,
                          system_prompt: selectedPrompt === 'none' ? null : selectedPrompt
                        })
                      })
                      
                      if (response.ok) {
                        // Update current state
                        setCurrentModel(selectedModel)
                        setCurrentPromptFile(selectedPrompt === 'none' ? null : selectedPrompt)
                        setMessages([])
                        
                        // Fetch the prompt content if a prompt was selected
                        if (selectedPrompt !== 'none') {
                          try {
                            const promptResponse = await fetch(`http://localhost:8100/api/v1/prompts/${selectedPrompt}`)
                            if (promptResponse.ok) {
                              const promptData = await promptResponse.json()
                              setCurrentPromptContent(promptData.content)
                            }
                          } catch (error) {
                            console.error('Failed to fetch prompt content:', error)
                          }
                        } else {
                          setCurrentPromptContent(null)
                        }
                        
                        setIsModalOpen(false)
                      }
                    } catch (error) {
                      console.error('Failed to create new conversation:', error)
                    }
                  }
                }}
              >
                Start New Chat
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* System Prompt Modal */}
        <Dialog open={isPromptModalOpen} onOpenChange={setIsPromptModalOpen}>
          <DialogContent className="w-[900px] max-w-[90vw] h-[90vh] max-h-[90vh] flex flex-col p-0" style={{ width: '900px', maxWidth: '90vw', height: '90vh', maxHeight: '90vh' }}>
            <DialogHeader className="p-6 border-b border-border">
              <DialogTitle className="text-2xl font-semibold">
                System Prompt{' '}
                {currentPromptFile && (
                  <span className="text-sm text-muted-foreground font-normal">{currentPromptFile}</span>
                )}
              </DialogTitle>
            </DialogHeader>

            {/* Prompt Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {currentPromptContent ? (
                <div className="prose prose-invert prose-base max-w-none
                  prose-p:my-3 prose-p:leading-relaxed prose-p:text-[15px]
                  prose-code:text-[13px] prose-code:bg-white/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono
                  prose-pre:bg-black/50 prose-pre:p-4 prose-pre:rounded-lg prose-pre:my-4 prose-pre:text-[14px]
                  prose-headings:my-4 prose-headings:font-semibold prose-headings:text-white prose-headings:leading-tight
                  prose-h1:text-2xl prose-h1:mb-6 prose-h1:mt-8 first:prose-h1:mt-0
                  prose-h2:text-xl prose-h2:mb-4 prose-h2:mt-6
                  prose-h3:text-lg prose-h3:mb-3 prose-h3:mt-5
                  prose-ul:my-3 prose-li:my-1 prose-li:text-[15px]
                  prose-ol:my-3 prose-ol:text-[15px]
                  prose-a:text-blue-400 prose-a:underline prose-a:text-[15px]
                  prose-blockquote:border-l-4 prose-blockquote:border-white/30 prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-[15px] prose-blockquote:my-4
                  prose-strong:font-bold prose-strong:text-white
                  prose-em:italic">
                  <ReactMarkdown components={markdownComponents}>
                    {currentPromptContent}
                  </ReactMarkdown>
                </div>
              ) : (
                <div className="flex items-center justify-center py-24 text-muted-foreground">
                  <div className="text-center">
                    <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">No system prompt</p>
                    <p className="text-sm mt-1">This conversation has no system prompt</p>
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </SidebarProvider>
  )
}

export default App
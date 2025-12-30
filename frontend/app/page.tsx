"use client"

import { useState, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Switch } from "@/components/ui/switch"
import {
  MessageSquare,
  BarChart3,
  Search,
  Info,
  Sparkles,
  TrendingUp,
  Database,
  Zap,
  CircleDot,
  Download,
  Trash2,
  Loader2,
  Building2,
  FileText,
  Activity,
  ChevronDown,
  ChevronUp,
  Globe,
  ExternalLink,
} from "lucide-react"
import { cn } from "@/lib/utils"
import ReactMarkdown from "react-markdown"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

export default function InvestIQDashboard() {
  const [apiStatus, setApiStatus] = useState<{
    connected: boolean
    companies: number
    message: string
  }>({ connected: false, companies: 0, message: "Checking..." })

  const [activeTab, setActiveTab] = useState("chat")

  useEffect(() => {
    checkAPIStatus()
  }, [])

  async function checkAPIStatus() {
    try {
      const response = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
      const data = await response.json()

      if (data.status === "ok") {
        setApiStatus({
          connected: true,
          companies: data.companies_indexed || 0,
          message: "Connected",
        })
      } else {
        setApiStatus({ connected: false, companies: 0, message: "API Error" })
      }
    } catch (error) {
      setApiStatus({ connected: false, companies: 0, message: "Disconnected" })
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-card/80 backdrop-blur-xl">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
                <Sparkles className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-foreground">InvestIQ</h1>
                <p className="text-xs text-muted-foreground">AI-Powered Investment Research</p>
              </div>
            </div>

            {/* API Status */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
                <CircleDot
                  className={cn(
                    "h-2 w-2",
                    apiStatus.connected ? "fill-green-500 text-green-500" : "fill-red-500 text-red-500",
                  )}
                />
                <span className="text-sm font-medium text-foreground">{apiStatus.message}</span>
                {apiStatus.companies > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {apiStatus.companies} companies
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {!apiStatus.connected && (
          <Card className="mb-6 border-destructive bg-destructive/10 p-6">
            <div className="flex items-start gap-4">
              <div className="rounded-lg bg-destructive/20 p-2">
                <Activity className="h-5 w-5 text-destructive" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-destructive">API Connection Required</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Cannot connect to API at {API_BASE}. Start your FastAPI server:
                </p>
                <code className="mt-2 block rounded bg-muted px-3 py-2 text-sm font-mono">python src/api/api.py</code>
              </div>
            </div>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
            <TabsTrigger value="chat" className="gap-2">
              <MessageSquare className="h-4 w-4" />
              <span className="hidden sm:inline">Chat</span>
            </TabsTrigger>
            <TabsTrigger value="dashboard" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </TabsTrigger>
            <TabsTrigger value="search" className="gap-2">
              <Search className="h-4 w-4" />
              <span className="hidden sm:inline">RAG Search</span>
            </TabsTrigger>
            <TabsTrigger value="about" className="gap-2">
              <Info className="h-4 w-4" />
              <span className="hidden sm:inline">About</span>
            </TabsTrigger>
          </TabsList>

          {/* Chat Tab */}
          <TabsContent value="chat" className="space-y-6">
            <ChatInterface apiBase={API_BASE} />
          </TabsContent>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            <DashboardGenerator apiBase={API_BASE} />
          </TabsContent>

          {/* Search Tab */}
          <TabsContent value="search" className="space-y-6">
            <RAGSearch apiBase={API_BASE} />
          </TabsContent>

          {/* About Tab */}
          <TabsContent value="about" className="space-y-6">
            <AboutSection />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

// Chat Interface Component
function ChatInterface({ apiBase }: { apiBase: string }) {
  const [companies, setCompanies] = useState<string[]>(["abridge"])
  const [selectedCompany, setSelectedCompany] = useState("abridge")
  const [chatHistory, setChatHistory] = useState<any[]>([])
  const [inputMessage, setInputMessage] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [enableWebSearch, setEnableWebSearch] = useState(false)

  useEffect(() => {
    fetchCompanies()
  }, [])

  async function fetchCompanies() {
    try {
      const response = await fetch(`${apiBase}/companies`)
      const data = await response.json()
      const companyList = Array.isArray(data) ? data : data.companies || []
      if (companyList.length > 0) {
        setCompanies(companyList.sort())
        setSelectedCompany(companyList[0])
      }
    } catch (error) {
      console.error("Failed to fetch companies:", error)
    }
  }

  async function sendMessage() {
    if (!inputMessage.trim() || isLoading) return

    const userMessage = { role: "user", content: inputMessage }
    setChatHistory((prev) => [...prev, userMessage])
    setInputMessage("")
    setIsLoading(true)

    try {
      const response = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: inputMessage,
          conversation_history: chatHistory,
          company_name: selectedCompany,
          model: "gpt-4o",
          temperature: 0.7,
          enable_web_search: enableWebSearch,
        }),
      })

      const data = await response.json()
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.message,
          used_retrieval: data.used_retrieval,
          used_web_search: data.used_web_search,
          chunks_retrieved: data.chunks_retrieved,
          company_name: data.company_name,
          chunks: data.chunks || [],
          web_sources: data.web_sources || [],
        },
      ])
    } catch (error) {
      console.error("Chat error:", error)
      setChatHistory((prev) => [...prev, { role: "assistant", content: "Error: Failed to get response from API." }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-3 flex flex-col" style={{ height: "calc(100vh - 280px)" }}>
        <div className="p-6 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-foreground">AI Assistant</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Ask questions about companies using RAG-powered intelligence
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => setChatHistory([])} className="gap-2">
              <Trash2 className="h-4 w-4" />
              Clear
            </Button>
          </div>

          <div className="mt-4 grid gap-4">
            <div>
              <Label htmlFor="company-select" className="text-sm font-medium">
                Select Company
              </Label>
              <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                <SelectTrigger id="company-select" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {companies.map((company) => (
                    <SelectItem key={company} value={company}>
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                        {company}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-card/50 p-3">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-muted-foreground" />
                <div>
                  <Label htmlFor="web-search-toggle" className="text-sm font-medium cursor-pointer">
                    Enable Web Search
                  </Label>
                  <p className="text-xs text-muted-foreground">Fallback to web if RAG finds no results</p>
                </div>
              </div>
              <Switch
                id="web-search-toggle"
                checked={enableWebSearch}
                onCheckedChange={setEnableWebSearch}
              />
            </div>
          </div>
        </div>

        <ScrollArea className="flex-1 p-6">
          <div className="space-y-4">
            {chatHistory.length === 0 && (
              <div className="flex min-h-[200px] flex-col items-center justify-center text-center">
                <div className="rounded-full bg-primary/10 p-4">
                  <MessageSquare className="h-8 w-8 text-primary" />
                </div>
                <h3 className="mt-4 text-lg font-semibold">Start a conversation</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Ask about {selectedCompany}'s funding, products, team, or strategy
                </p>
              </div>
            )}

            {chatHistory.map((msg, idx) => (
              <div key={idx} className={cn("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[80%] rounded-2xl px-4 py-3",
                    msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
                  )}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  {msg.used_retrieval && msg.chunks && msg.chunks.length > 0 && (
                    <Collapsible className="mt-3">
                      <CollapsibleTrigger className="flex items-center gap-2 text-xs opacity-70 hover:opacity-100 transition-opacity">
                        <Database className="h-3 w-3" />
                        <span>Retrieved {msg.chunks_retrieved} chunks from {msg.company_name}</span>
                        <ChevronDown className="h-3 w-3" />
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2 space-y-2">
                        {msg.chunks.map((chunk: any, chunkIdx: number) => (
                          <div key={chunkIdx} className="rounded-lg border border-border bg-card p-3 text-xs">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <FileText className="h-3 w-3 text-muted-foreground" />
                                <span className="font-medium text-foreground">{chunk.source_type}</span>
                                <Badge variant="outline" className="text-xs">
                                  Chunk {chunk.chunk_index + 1}
                                </Badge>
                              </div>
                              {chunk.distance && (
                                <span className="text-muted-foreground">
                                  Distance: {chunk.distance.toFixed(3)}
                                </span>
                              )}
                            </div>
                            {chunk.source_url && (
                              <a
                                href={chunk.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block mb-2 text-primary hover:underline truncate"
                              >
                                {chunk.source_url}
                              </a>
                            )}
                            <div className="text-muted-foreground leading-relaxed max-h-32 overflow-y-auto">
                              {chunk.text}
                            </div>
                          </div>
                        ))}
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                  {msg.used_retrieval && (!msg.chunks || msg.chunks.length === 0) && (
                    <div className="mt-2 flex items-center gap-2 text-xs opacity-70">
                      <Database className="h-3 w-3" />
                      Retrieved {msg.chunks_retrieved} chunks from {msg.company_name}
                    </div>
                  )}
                  
                  {msg.used_web_search && msg.web_sources && msg.web_sources.length > 0 && (
                    <Collapsible className="mt-3">
                      <CollapsibleTrigger className="flex items-center gap-2 text-xs opacity-70 hover:opacity-100 transition-opacity">
                        <Globe className="h-3 w-3" />
                        <span>Found {msg.web_sources.length} web results</span>
                        <ChevronDown className="h-3 w-3" />
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2 space-y-2">
                        {msg.web_sources.map((source: any, sourceIdx: number) => (
                          <div key={sourceIdx} className="rounded-lg border border-green-500/20 bg-green-500/5 p-3 text-xs">
                            <div className="flex items-start gap-2 mb-2">
                              <Globe className="h-3 w-3 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <div className="font-medium text-foreground mb-1 flex items-center gap-2">
                                  {source.title}
                                  <Badge variant="outline" className="bg-green-500/10 text-green-700 dark:text-green-300 border-green-500/30">
                                    Web
                                  </Badge>
                                </div>
                                {source.url && (
                                  <a
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-green-600 dark:text-green-400 hover:underline mb-2 truncate"
                                  >
                                    {source.url}
                                    <ExternalLink className="h-3 w-3 flex-shrink-0" />
                                  </a>
                                )}
                                <div className="text-muted-foreground leading-relaxed">
                                  {source.snippet}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3">
                <div className="max-w-[80%] rounded-2xl bg-muted px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="p-6 flex-shrink-0">
          <div className="flex gap-3">
            <Input
              placeholder={`Ask about ${selectedCompany}...`}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              disabled={isLoading}
              className="flex-1"
            />
            <Button onClick={sendMessage} disabled={isLoading || !inputMessage.trim()}>
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Dashboard Generator Component
function DashboardGenerator({ apiBase }: { apiBase: string }) {
  const [companies, setCompanies] = useState<string[]>(["abridge"])
  const [selectedCompany, setSelectedCompany] = useState("abridge")
  const [topK, setTopK] = useState(15)
  const [maxTokens, setMaxTokens] = useState(4000)
  const [temperature, setTemperature] = useState(0.3)
  const [model, setModel] = useState("gpt-4o")
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<any>(null)

  useEffect(() => {
    fetchCompanies()
  }, [])

  async function fetchCompanies() {
    try {
      const response = await fetch(`${apiBase}/companies`)
      const data = await response.json()
      const companyList = Array.isArray(data) ? data : data.companies || []
      if (companyList.length > 0) {
        setCompanies(companyList.sort())
        setSelectedCompany(companyList[0])
      }
    } catch (error) {
      console.error("Failed to fetch companies:", error)
    }
  }

  async function generateDashboard() {
    setIsGenerating(true)
    setProgress(25)
    setResult(null)

    try {
      setProgress(50)
      const response = await fetch(`${apiBase}/dashboard/rag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: selectedCompany,
          top_k: topK,
          max_tokens: maxTokens,
          temperature,
          model,
        }),
      })

      setProgress(75)
      const data = await response.json()
      setProgress(100)
      setResult(data)
    } catch (error) {
      console.error("Generation error:", error)
    } finally {
      setIsGenerating(false)
      setTimeout(() => setProgress(0), 1000)
    }
  }

  function downloadDashboard() {
    if (!result) return
    const blob = new Blob([result.dashboard], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${selectedCompany}_investment_dashboard.md`
    a.click()
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Configuration Panel */}
      <Card className="p-6">
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold text-foreground">Generate Dashboard</h2>
            <p className="mt-1 text-sm text-muted-foreground">8-section investment analysis using RAG</p>
          </div>

          <div className="space-y-4">
            <div>
              <Label htmlFor="company">Company</Label>
              <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                <SelectTrigger id="company" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {companies.map((company) => (
                    <SelectItem key={company} value={company}>
                      {company}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="top-k">Context Chunks: {topK}</Label>
              <Slider
                id="top-k"
                min={5}
                max={30}
                step={1}
                value={[topK]}
                onValueChange={([value]) => setTopK(value)}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="max-tokens">Max Tokens</Label>
              <Select value={maxTokens.toString()} onValueChange={(v) => setMaxTokens(Number(v))}>
                <SelectTrigger id="max-tokens" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2000">2000 tokens</SelectItem>
                  <SelectItem value="4000">4000 tokens</SelectItem>
                  <SelectItem value="6000">6000 tokens</SelectItem>
                  <SelectItem value="8000">8000 tokens</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="temperature">Temperature: {temperature}</Label>
              <Slider
                id="temperature"
                min={0}
                max={1}
                step={0.1}
                value={[temperature]}
                onValueChange={([value]) => setTemperature(value)}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="model">Model</Label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger id="model" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                  <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                  <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button onClick={generateDashboard} disabled={isGenerating} className="w-full gap-2" size="lg">
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" />
                Generate Dashboard
              </>
            )}
          </Button>

          {progress > 0 && <Progress value={progress} className="h-2" />}
        </div>
      </Card>

      {/* Results Panel */}
      <Card className="lg:col-span-2">
        {!result ? (
          <div className="flex h-full min-h-[600px] flex-col items-center justify-center p-6 text-center">
            <div className="rounded-full bg-primary/10 p-6">
              <BarChart3 className="h-12 w-12 text-primary" />
            </div>
            <h3 className="mt-6 text-xl font-semibold">Ready to generate</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Configure your settings and click Generate Dashboard to create an 8-section investment analysis
            </p>
            <div className="mt-6 grid gap-2 text-left text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                Company Overview & Business Model
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                Funding & Growth Momentum
              </div>
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                Market Sentiment & Risk Analysis
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="border-b border-border p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold">Investment Dashboard</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Analysis for {selectedCompany}</p>
                </div>
                <Button onClick={downloadDashboard} variant="outline" size="sm" className="gap-2 bg-transparent">
                  <Download className="h-4 w-4" />
                  Download
                </Button>
              </div>

              {/* Metrics */}
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-border bg-card p-3">
                  <div className="text-xs text-muted-foreground">Chunks Retrieved</div>
                  <div className="mt-1 text-xl font-bold">{result.metadata?.chunks_retrieved || 0}</div>
                </div>
                <div className="rounded-lg border border-border bg-card p-3">
                  <div className="text-xs text-muted-foreground">Total Tokens</div>
                  <div className="mt-1 text-xl font-bold">{result.metadata?.tokens_used?.total || 0}</div>
                </div>
                <div className="rounded-lg border border-border bg-card p-3">
                  <div className="text-xs text-muted-foreground">Sources</div>
                  <div className="mt-1 text-xl font-bold">{result.context_sources?.length || 0}</div>
                </div>
                <div className="rounded-lg border border-border bg-card p-3">
                  <div className="text-xs text-muted-foreground">Sections</div>
                  <div className="mt-1 text-xl font-bold">{result.metadata?.sections_present || 8}</div>
                </div>
              </div>

              {result.context_sources && result.context_sources.length > 0 && (
                <div className="mt-4">
                  <div className="text-xs font-medium text-muted-foreground">Sources used:</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.context_sources.map((source: string, idx: number) => (
                      <Badge key={idx} variant="secondary">
                        {source}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <ScrollArea className="h-[600px] p-6">
              <div className="markdown-content">
                <ReactMarkdown
                  components={{
                    h1: ({ children }) => (
                      <h1 className="text-3xl font-bold mb-4 mt-6 text-foreground border-b border-border pb-2">
                        {children}
                      </h1>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-2xl font-bold mb-3 mt-5 text-foreground border-b border-border pb-2">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-xl font-semibold mb-2 mt-4 text-foreground">
                        {children}
                      </h3>
                    ),
                    h4: ({ children }) => (
                      <h4 className="text-lg font-semibold mb-2 mt-3 text-foreground">
                        {children}
                      </h4>
                    ),
                    p: ({ children }) => (
                      <p className="mb-4 text-foreground leading-7">{children}</p>
                    ),
                    ul: ({ children }) => (
                      <ul className="mb-4 ml-6 list-disc space-y-2 text-foreground">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="mb-4 ml-6 list-decimal space-y-2 text-foreground">
                        {children}
                      </ol>
                    ),
                    li: ({ children }) => (
                      <li className="text-foreground">{children}</li>
                    ),
                    strong: ({ children }) => (
                      <strong className="font-semibold text-foreground">{children}</strong>
                    ),
                    em: ({ children }) => (
                      <em className="italic text-foreground">{children}</em>
                    ),
                    code: ({ children, className, ...props }) => {
                      const isInline = !className
                      return isInline ? (
                        <code className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono text-foreground" {...props}>
                          {children}
                        </code>
                      ) : (
                        <code className={cn("block rounded-lg bg-muted p-4 text-sm font-mono text-foreground overflow-x-auto", className)} {...props}>
                          {children}
                        </code>
                      )
                    },
                    pre: ({ children }) => {
                      const codeElement = (children as any)?.props?.children
                      return (
                        <pre className="mb-4 rounded-lg bg-muted p-4 overflow-x-auto">
                          {children}
                        </pre>
                      )
                    },
                    blockquote: ({ children }) => (
                      <blockquote className="mb-4 border-l-4 border-primary pl-4 italic text-muted-foreground">
                        {children}
                      </blockquote>
                    ),
                    hr: () => (
                      <hr className="my-6 border-border" />
                    ),
                    a: ({ href, children }) => (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        {children}
                      </a>
                    ),
                    table: ({ children }) => (
                      <div className="mb-4 overflow-x-auto">
                        <table className="min-w-full border-collapse border border-border">
                          {children}
                        </table>
                      </div>
                    ),
                    thead: ({ children }) => (
                      <thead className="bg-muted">{children}</thead>
                    ),
                    tbody: ({ children }) => (
                      <tbody>{children}</tbody>
                    ),
                    tr: ({ children }) => (
                      <tr className="border-b border-border">{children}</tr>
                    ),
                    th: ({ children }) => (
                      <th className="border border-border px-4 py-2 text-left font-semibold text-foreground">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="border border-border px-4 py-2 text-foreground">
                        {children}
                      </td>
                    ),
                  }}
                >
                  {result.dashboard}
                </ReactMarkdown>
              </div>
            </ScrollArea>
          </>
        )}
      </Card>
    </div>
  )
}

// RAG Search Component
function RAGSearch({ apiBase }: { apiBase: string }) {
  const [companies, setCompanies] = useState<string[]>(["abridge"])
  const [selectedCompany, setSelectedCompany] = useState("abridge")
  const [query, setQuery] = useState("funding")
  const [topK, setTopK] = useState(5)
  const [sourceFilter, setSourceFilter] = useState("all")
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<any>(null)

  useEffect(() => {
    fetchCompanies()
  }, [])

  async function fetchCompanies() {
    try {
      const response = await fetch(`${apiBase}/companies`)
      const data = await response.json()
      const companyList = Array.isArray(data) ? data : data.companies || []
      if (companyList.length > 0) {
        setCompanies(companyList.sort())
        setSelectedCompany(companyList[0])
      }
    } catch (error) {
      console.error("Failed to fetch companies:", error)
    }
  }

  async function performSearch() {
    setIsSearching(true)
    setResults(null)

    try {
      const params = new URLSearchParams({
        company_name: selectedCompany,
        query,
        top_k: topK.toString(),
      })
      if (sourceFilter !== "all") {
        params.append("filter_source", sourceFilter)
      }

      const response = await fetch(`${apiBase}/rag/search?${params}`)
      const data = await response.json()
      setResults(data)
    } catch (error) {
      console.error("Search error:", error)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Search Panel */}
      <Card className="p-6">
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold text-foreground">Semantic Search</h2>
            <p className="mt-1 text-sm text-muted-foreground">Search through company data using vector embeddings</p>
          </div>

          <div className="space-y-4">
            <div>
              <Label htmlFor="search-company">Company</Label>
              <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                <SelectTrigger id="search-company" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {companies.map((company) => (
                    <SelectItem key={company} value={company}>
                      {company}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="search-query">Search Query</Label>
              <Input
                id="search-query"
                placeholder="e.g., funding, leadership, product"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && performSearch()}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="results-count">Results: {topK}</Label>
              <Slider
                id="results-count"
                min={1}
                max={20}
                step={1}
                value={[topK]}
                onValueChange={([value]) => setTopK(value)}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="source-filter">Source Filter</Label>
              <Select value={sourceFilter} onValueChange={setSourceFilter}>
                <SelectTrigger id="source-filter" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  <SelectItem value="homepage">Homepage</SelectItem>
                  <SelectItem value="about">About</SelectItem>
                  <SelectItem value="product">Product</SelectItem>
                  <SelectItem value="careers">Careers</SelectItem>
                  <SelectItem value="blog">Blog</SelectItem>
                  <SelectItem value="news">News</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button onClick={performSearch} disabled={isSearching || !query.trim()} className="w-full gap-2" size="lg">
            {isSearching ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                Search
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Results Panel */}
      <Card className="lg:col-span-2">
        {!results ? (
          <div className="flex h-full min-h-[600px] flex-col items-center justify-center p-6 text-center">
            <div className="rounded-full bg-accent/10 p-6">
              <Search className="h-12 w-12 text-accent" />
            </div>
            <h3 className="mt-6 text-xl font-semibold">Ready to search</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Enter your search query to find relevant chunks from the vector database
            </p>
          </div>
        ) : (
          <>
            <div className="border-b border-border p-6">
              <h3 className="text-xl font-bold">Search Results</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Found {results.total_results || 0} relevant chunks for "{results.query}"
              </p>

              {results.results && results.results.length > 0 && (
                <div className="mt-4 grid grid-cols-3 gap-3">
                  <div className="rounded-lg border border-border bg-card p-3">
                    <div className="text-xs text-muted-foreground">Company</div>
                    <div className="mt-1 font-semibold">{results.company_name}</div>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <div className="text-xs text-muted-foreground">Results</div>
                    <div className="mt-1 font-semibold">{results.total_results}</div>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <div className="text-xs text-muted-foreground">Avg Distance</div>
                    <div className="mt-1 font-semibold">
                      {(
                        results.results.reduce((sum: number, r: any) => sum + (r.distance || 0), 0) /
                        results.results.length
                      ).toFixed(3)}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <ScrollArea className="h-[600px] p-6">
              <div className="space-y-4">
                {results.results?.map((result: any, idx: number) => {
                  const distance = result.distance || 0
                  const quality = distance < 1.0 ? "Excellent" : distance < 1.5 ? "Good" : "Fair"
                  const qualityColor =
                    distance < 1.0 ? "text-green-500" : distance < 1.5 ? "text-yellow-500" : "text-orange-500"

                  return (
                    <Card key={idx} className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{result.source_type}</span>
                          <Badge variant="outline" className={qualityColor}>
                            {quality}
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">Distance: {distance.toFixed(3)}</span>
                      </div>

                      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                        <div>Chunk: {result.chunk_index + 1}</div>
                        <div>Size: {result.chunk_size || 0} chars</div>
                      </div>

                      {result.source_url && (
                        <a
                          href={result.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2 block truncate text-xs text-primary hover:underline"
                        >
                          {result.source_url}
                        </a>
                      )}

                      <Textarea value={result.text} readOnly className="mt-3 font-mono text-xs" rows={6} />
                    </Card>
                  )
                })}

                {results.results?.length === 0 && (
                  <div className="flex h-[400px] flex-col items-center justify-center text-center">
                    <Search className="h-12 w-12 text-muted-foreground" />
                    <p className="mt-4 text-sm text-muted-foreground">No results found for "{results.query}"</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </>
        )}
      </Card>
    </div>
  )
}

// About Section Component
function AboutSection() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-primary/10 p-3">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold">About InvestIQ</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              InvestIQ is a RAG-powered startup investment analysis system that combines vector database search with
              large language models to generate comprehensive investment research dashboards.
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <div className="flex items-start gap-3">
            <div className="rounded bg-primary/10 p-2">
              <Database className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold">Vector Database</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                Semantic search using ChromaDB with embedded company data
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="rounded bg-primary/10 p-2">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold">LLM Integration</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                GPT-4o powered analysis with retrieval augmented generation
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="rounded bg-primary/10 p-2">
              <BarChart3 className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold">8-Section Analysis</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                Comprehensive investment dashboards covering all key areas
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <h3 className="text-lg font-bold">Dashboard Sections</h3>
        <div className="mt-4 space-y-3">
          {[
            "Company Overview",
            "Business Model and GTM",
            "Funding & Investor Profile",
            "Growth Momentum",
            "Visibility & Market Sentiment",
            "Risks and Challenges",
            "Outlook",
            "Disclosure Gaps",
          ].map((section, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <div className="flex h-6 w-6 items-center justify-center rounded bg-primary/10 text-xs font-semibold text-primary">
                {idx + 1}
              </div>
              <span className="text-sm">{section}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-6 lg:col-span-2">
        <h3 className="text-lg font-bold">Technical Stack</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-border p-4">
            <div className="font-semibold">Frontend</div>
            <p className="mt-2 text-sm text-muted-foreground">Next.js 16, React 19, TailwindCSS, shadcn/ui</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <div className="font-semibold">Backend</div>
            <p className="mt-2 text-sm text-muted-foreground">FastAPI, Python, ChromaDB, OpenAI API</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <div className="font-semibold">AI/ML</div>
            <p className="mt-2 text-sm text-muted-foreground">GPT-4o, Embeddings, RAG Pipeline, Vector Search</p>
          </div>
        </div>
      </Card>
    </div>
  )
}

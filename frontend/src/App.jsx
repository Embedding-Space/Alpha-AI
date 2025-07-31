import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ThemeProvider } from '@/components/theme-provider'

function App() {
  const [message, setMessage] = useState('Ready to make this UI sexy as fuck! 🚀')

  return (
    <ThemeProvider defaultTheme="system" storageKey="alpha-ai-theme">
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-3xl font-bold text-center">Alpha AI</CardTitle>
            <CardDescription className="text-center">React Edition with shadcn/ui</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-center">{message}</p>
            </div>
            <Button 
              onClick={() => setMessage("Let's build something amazing together!")}
              className="w-full"
            >
              Click for Alpha vibes
            </Button>
          </CardContent>
        </Card>
      </div>
    </ThemeProvider>
  )
}

export default App
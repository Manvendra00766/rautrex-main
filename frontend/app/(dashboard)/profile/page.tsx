'use client'

import React, { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

export default function ProfilePage() {
  const { user } = useAuthStore()
  const supabase = createClient()
  
  const [profile, setProfile] = useState<any>(null)
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  
  const [portfolios, setPortfolios] = useState<any[]>([])
  const [watchlists, setWatchlists] = useState<any[]>([])
  const [backtests, setBacktests] = useState<any[]>([])
  const [signals, setSignals] = useState<any[]>([])

  useEffect(() => {
    if (user) {
      fetchProfile()
      fetchData()
    }
  }, [user])

  async function fetchProfile() {
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user?.id)
        .single()

      if (error) throw error
      setProfile(data)
      setFullName(data.full_name || '')
    } catch (error: any) {
      console.error('Error fetching profile:', error.message)
    } finally {
      setLoading(false)
    }
  }

  async function fetchData() {
    const [pRes, wRes, bRes, sRes] = await Promise.all([
      supabase.from('portfolios').select('*, portfolio_positions(count)'),
      supabase.from('watchlists').select('*, watchlist_items(count)'),
      supabase.from('saved_backtests').select('*'),
      supabase.from('saved_signals').select('*')
    ])

    if (pRes.data) setPortfolios(pRes.data)
    if (wRes.data) setWatchlists(wRes.data)
    if (bRes.data) setBacktests(bRes.data)
    if (sRes.data) setSignals(sRes.data)
    
    setLoading(false)
  }

  async function deletePortfolio(id: string) {
    if (!confirm('Are you sure you want to delete this portfolio?')) return
    
    try {
      const { error } = await supabase.from('portfolios').delete().eq('id', id)
      if (error) throw error
      setPortfolios(portfolios.filter(p => p.id !== id))
      alert('Portfolio deleted')
    } catch (error: any) {
      alert('Error deleting portfolio: ' + error.message)
    }
  }

  async function updateProfile() {
    try {
      const { error } = await supabase
        .from('profiles')
        .update({ full_name: fullName })
        .eq('id', user?.id)

      if (error) throw error
      alert('Profile updated successfully')
    } catch (error: any) {
      alert('Error updating profile: ' + error.message)
    }
  }

  async function uploadAvatar(event: React.ChangeEvent<HTMLInputElement>) {
    try {
      setUploading(true)
      if (!event.target.files || event.target.files.length === 0) {
        throw new Error('You must select an image to upload.')
      }

      const file = event.target.files[0]
      const fileExt = file.name.split('.').pop()
      const filePath = `${user?.id}/avatar.${fileExt}`

      const { error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(filePath, file, { upsert: true })

      if (uploadError) throw uploadError

      const { data: { publicUrl } } = supabase.storage
        .from('avatars')
        .getPublicUrl(filePath)

      const { error: updateError } = await supabase
        .from('profiles')
        .update({ avatar_url: publicUrl })
        .eq('id', user?.id)

      if (updateError) throw updateError
      
      setProfile({ ...profile, avatar_url: publicUrl })
      alert('Avatar updated successfully')
    } catch (error: any) {
      alert('Error uploading avatar: ' + error.message)
    } finally {
      setUploading(false)
    }
  }

  if (loading) return <div className="p-8">Loading profile...</div>

  return (
    <div className="container mx-auto py-10 px-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Profile Sidebar */}
        <Card className="md:col-span-1">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <div className="relative">
                <Avatar className="h-24 w-24">
                  <AvatarImage src={profile?.avatar_url} />
                  <AvatarFallback>{user?.email?.charAt(0).toUpperCase()}</AvatarFallback>
                </Avatar>
                <Label 
                  htmlFor="avatar-upload" 
                  className="absolute bottom-0 right-0 bg-primary text-primary-foreground p-1 rounded-full cursor-pointer hover:opacity-90"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
                  <input 
                    id="avatar-upload" 
                    type="file" 
                    accept="image/*" 
                    className="hidden" 
                    onChange={uploadAvatar} 
                    disabled={uploading}
                  />
                </Label>
              </div>
            </div>
            <CardTitle>{fullName || 'User Profile'}</CardTitle>
            <CardDescription>{user?.email}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <Input 
                id="fullName" 
                value={fullName} 
                onChange={(e) => setFullName(e.target.value)} 
                placeholder="Enter your name"
              />
            </div>
            <Button className="w-full" onClick={updateProfile}>Save Changes</Button>
            
            <div className="pt-6 space-y-4">
              <div className="flex justify-between text-sm">
                <span>Account Status</span>
                <span className="text-green-500 font-medium">Verified</span>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span>Storage Usage</span>
                  <span>12%</span>
                </div>
                <Progress value={12} className="h-1" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Content Tabs */}
        <Card className="md:col-span-2">
          <Tabs defaultValue="portfolios">
            <TabsList className="w-full justify-start border-b rounded-none px-4 h-12 bg-transparent">
              <TabsTrigger value="portfolios" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none bg-transparent">Portfolios</TabsTrigger>
              <TabsTrigger value="watchlists" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none bg-transparent">Watchlists</TabsTrigger>
              <TabsTrigger value="backtests" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none bg-transparent">Backtests</TabsTrigger>
              <TabsTrigger value="signals" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none bg-transparent">Signals</TabsTrigger>
            </TabsList>
            
            <TabsContent value="portfolios" className="p-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Positions</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {portfolios.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-medium">{p.name}</TableCell>
                      <TableCell>{p.portfolio_positions?.[0]?.count || 0}</TableCell>
                      <TableCell>{new Date(p.created_at).toLocaleDateString()}</TableCell>
                      <TableCell className="text-right flex justify-end gap-2">
                        <Button variant="ghost" size="sm">View</Button>
                        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => deletePortfolio(p.id)}>Delete</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {portfolios.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-4 text-muted-foreground">No portfolios found</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="watchlists" className="p-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Items</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {watchlists.map((w) => (
                    <TableRow key={w.id}>
                      <TableCell className="font-medium">{w.name}</TableCell>
                      <TableCell>{w.watchlist_items?.[0]?.count || 0}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm">View</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {watchlists.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center py-4 text-muted-foreground">No watchlists found</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="backtests" className="p-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Strategy</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {backtests.map((b) => (
                    <TableRow key={b.id}>
                      <TableCell className="font-medium">{b.name}</TableCell>
                      <TableCell>{b.ticker}</TableCell>
                      <TableCell>{b.strategy}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm">Results</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {backtests.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-4 text-muted-foreground">No saved backtests found</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="signals" className="p-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {signals.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">{s.ticker}</TableCell>
                      <TableCell>{s.signal_type}</TableCell>
                      <TableCell>{new Date(s.created_at).toLocaleDateString()}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm">View</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {signals.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-4 text-muted-foreground">No saved signals found</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TabsContent>
          </Tabs>
        </Card>
      </div>
    </div>
  )
}

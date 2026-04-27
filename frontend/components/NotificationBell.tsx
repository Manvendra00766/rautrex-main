"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Bell, Check, Trash2, BrainCircuit, Activity, ShieldAlert, Newspaper, Terminal } from "lucide-react";
import { createClient } from "@/lib/supabase";
import { useAuthStore } from "@/lib/auth-store";
import { useToast } from "@/components/ui/Toast";
import { apiFetch } from "@/lib/api";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

export default function NotificationBell() {
  const { user } = useAuthStore();
  const { toast } = useToast();
  const supabase = createClient();
  
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const data = await apiFetch("/notifications/");
      setNotifications(data || []);
      
      const countData = await apiFetch("/notifications/unread-count");
      setUnreadCount(countData.unread_count || 0);
    } catch (err) {
      console.error("Failed to fetch notifications", err);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  useEffect(() => {
    if (!user) return;

    const channel = supabase
      .channel("notifications")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          table: "notifications",
          filter: `user_id=eq.${user.id}`,
        },
        (payload) => {
          const newNotif = payload.new;
          setNotifications((prev) => [newNotif, ...prev]);
          setUnreadCount((prev) => prev + 1);
          
          toast({
            type: 'info',
            title: newNotif.title,
            description: newNotif.body,
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user, supabase, toast]);

  const markAllRead = async () => {
    try {
      await apiFetch("/notifications/read-all", { method: 'PATCH' });
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast({ type: 'success', title: 'Success', description: 'All notifications marked as read.' });
    } catch (err) {
      console.error("Failed to mark all read", err);
      toast({ type: 'error', title: 'Error', description: 'Failed to mark all as read.' });
    }
  };

  const markRead = async (id: string) => {
    try {
      await apiFetch(`/notifications/${id}/read`, { method: 'PATCH' });
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to mark read", err);
    }
  };

  const deleteNotif = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await apiFetch(`/notifications/${id}`, { method: 'DELETE' });
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      const notif = notifications.find(n => n.id === id);
      if (notif && !notif.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error("Failed to delete notification", err);
      toast({ type: 'error', title: 'Error', description: 'Failed to delete notification.' });
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "signal": return <BrainCircuit className="text-cyan-400" size={16} />;
      case "price_alert": return <Activity className="text-green-400" size={16} />;
      case "backtest_complete": return <Terminal className="text-amber-400" size={16} />;
      case "portfolio": return <ShieldAlert className="text-purple-400" size={16} />;
      case "system": return <Newspaper className="text-gray-400" size={16} />;
      default: return <Bell size={16} />;
    }
  };

  const renderNotifList = (filterType?: string) => {
    const filtered = filterType 
      ? notifications.filter(n => {
          if (filterType === 'signals') return n.type === 'signal';
          if (filterType === 'prices') return n.type === 'price_alert';
          if (filterType === 'portfolio') return n.type === 'portfolio';
          if (filterType === 'system') return n.type === 'system' || n.type === 'backtest_complete';
          return true;
        })
      : notifications;

    if (filtered.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-gray-500 opacity-50">
          <Bell size={40} className="mb-2" />
          <p className="text-xs">No notifications here</p>
        </div>
      );
    }

    return (
      <div className="max-h-[400px] overflow-auto divide-y divide-white/5">
        {filtered.map((n) => (
          <div
            key={n.id}
            onClick={() => !n.is_read && markRead(n.id)}
            className={cn(
              "p-4 hover:bg-white/5 transition-colors cursor-pointer relative group",
              !n.is_read && "bg-accent/5"
            )}
          >
            {!n.is_read && <div className="absolute left-0 top-0 bottom-0 w-1 bg-accent" />}
            <div className="flex gap-3">
              <div className="shrink-0 mt-1">{getIcon(n.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start gap-2">
                  <h4 className={cn("text-xs font-bold truncate", n.is_read ? "text-gray-400" : "text-white")}>
                    {n.title}
                  </h4>
                  <span className="text-[10px] text-gray-500 whitespace-nowrap">
                    {n.created_at ? formatDistanceToNow(new Date(n.created_at), { addSuffix: true }) : ''}
                  </span>
                </div>
                <p className="text-[11px] text-gray-500 line-clamp-2 mt-0.5 leading-relaxed">
                  {n.body}
                </p>
              </div>
              <button 
                onClick={(e) => deleteNotif(e, n.id)}
                className="opacity-0 group-hover:opacity-100 h-6 w-6 flex items-center justify-center hover:bg-red-500/10 hover:text-red-500 rounded transition-all"
              >
                <Trash2 size={12} />
              </button>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button className="text-gray-400 hover:text-white relative p-2 rounded-full hover:bg-white/5 transition-colors">
          <Bell size={20} />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 bg-accent text-[10px] font-bold text-white rounded-full flex items-center justify-center border-2 border-[#0a0a0f]">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0 bg-surface border-white/10 shadow-2xl overflow-hidden rounded-2xl" align="end">
        <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/5">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            Notifications {unreadCount > 0 && <span className="text-accent text-xs">({unreadCount} new)</span>}
          </h3>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={markAllRead} 
            className="h-7 text-[10px] font-bold gap-1.5 text-accent hover:text-accent hover:bg-accent/10"
            disabled={unreadCount === 0}
          >
            <Check size={12} /> MARK ALL AS READ
          </Button>
        </div>

        <Tabs defaultValue="all" className="w-full">
          <TabsList className="w-full bg-transparent border-b border-white/5 rounded-none h-10 px-2 justify-start gap-4">
            <TabsTrigger value="all" className="text-[10px] uppercase font-bold data-[state=active]:bg-transparent data-[state=active]:text-accent data-[state=active]:border-b-2 data-[state=active]:border-accent rounded-none px-1 h-full border-b-2 border-transparent">All</TabsTrigger>
            <TabsTrigger value="signals" className="text-[10px] uppercase font-bold data-[state=active]:bg-transparent data-[state=active]:text-accent data-[state=active]:border-b-2 data-[state=active]:border-accent rounded-none px-1 h-full border-b-2 border-transparent">Signals</TabsTrigger>
            <TabsTrigger value="prices" className="text-[10px] uppercase font-bold data-[state=active]:bg-transparent data-[state=active]:text-accent data-[state=active]:border-b-2 data-[state=active]:border-accent rounded-none px-1 h-full border-b-2 border-transparent">Prices</TabsTrigger>
            <TabsTrigger value="portfolio" className="text-[10px] uppercase font-bold data-[state=active]:bg-transparent data-[state=active]:text-accent data-[state=active]:border-b-2 data-[state=active]:border-accent rounded-none px-1 h-full border-b-2 border-transparent">Portfolio</TabsTrigger>
            <TabsTrigger value="system" className="text-[10px] uppercase font-bold data-[state=active]:bg-transparent data-[state=active]:text-accent data-[state=active]:border-b-2 data-[state=active]:border-accent rounded-none px-1 h-full border-b-2 border-transparent">System</TabsTrigger>
          </TabsList>
          
          <TabsContent value="all" className="mt-0">{renderNotifList()}</TabsContent>
          <TabsContent value="signals" className="mt-0">{renderNotifList('signals')}</TabsContent>
          <TabsContent value="prices" className="mt-0">{renderNotifList('prices')}</TabsContent>
          <TabsContent value="portfolio" className="mt-0">{renderNotifList('portfolio')}</TabsContent>
          <TabsContent value="system" className="mt-0">{renderNotifList('system')}</TabsContent>
        </Tabs>

        <div className="p-3 border-t border-white/5 bg-white/5 text-center">
            <button className="text-[10px] font-bold text-gray-500 hover:text-white transition-colors uppercase tracking-widest">
                View All Activity
            </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

import React, { createContext, useContext, useState } from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import NotificationBell from '@/components/NotificationBell';
import { createClient } from '@/lib/supabase';
import { useAuthStore } from '@/lib/auth-store';
import { useToast } from '@/components/ui/Toast';
import api from '@/lib/api';

// Mocks
jest.mock('@/lib/supabase');
jest.mock('@/lib/auth-store');
jest.mock('@/components/ui/Toast');
jest.mock('@/lib/api');

// Context-based mock for Radix UI Popover
const PopoverContext = createContext<any>(null);
jest.mock('@radix-ui/react-popover', () => {
  const React = require('react');
  return {
    Root: ({ children, open, onOpenChange }: any) => {
      const [isOpen, setIsOpen] = React.useState(open || false);
      const value = React.useMemo(() => ({
        isOpen,
        setIsOpen: (val: boolean) => {
            setIsOpen(val);
            onOpenChange?.(val);
        }
      }), [isOpen]);
      return <div className="popover-root"><PopoverContext.Provider value={value}>{children}</PopoverContext.Provider></div>;
    },
    Trigger: ({ children, asChild }: any) => {
      const { isOpen, setIsOpen } = useContext(PopoverContext);
      const props = {
        onClick: () => setIsOpen(!isOpen),
        'data-testid': "popover-trigger"
      };
      if (asChild && React.isValidElement(children)) {
        return React.cloneElement(children as any, props);
      }
      return <button {...props}>{children}</button>;
    },
    Portal: ({ children }: any) => {
      const { isOpen } = useContext(PopoverContext);
      return isOpen ? <div data-testid="popover-portal">{children}</div> : null;
    },
    Content: ({ children }: any) => <div data-testid="popover-content">{children}</div>,
    Anchor: ({ children }: any) => <div>{children}</div>,
  };
});

// Context-based mock for Radix UI Tabs
const TabsContext = createContext<any>(null);
jest.mock('@radix-ui/react-tabs', () => {
  const React = require('react');
  return {
    Root: ({ children, defaultValue, value: controlledValue, onValueChange }: any) => {
      const [internalValue, setInternalValue] = React.useState(defaultValue);
      const value = controlledValue !== undefined ? controlledValue : internalValue;
      const setValue = (val: string) => {
        setInternalValue(val);
        onValueChange?.(val);
      };
      const contextValue = React.useMemo(() => ({ value, setValue }), [value]);
      return <div className="tabs-root"><TabsContext.Provider value={contextValue}>{children}</TabsContext.Provider></div>;
    },
    List: ({ children }: any) => <div role="tablist">{children}</div>,
    Trigger: ({ children, value }: any) => {
      const { value: activeValue, setValue } = useContext(TabsContext);
      return (
        <button 
          role="tab" 
          aria-selected={value === activeValue}
          onClick={() => setValue(value)}
        >
          {children}
        </button>
      );
    },
    Content: ({ children, value }: any) => {
      const { value: activeValue } = useContext(TabsContext);
      return value === activeValue ? <div>{children}</div> : null;
    },
  };
});

const mockUser = { id: 'user-123' };

describe('NotificationBell Realtime & UI', () => {
  let mockSupabase: any;
  let mockChannel: any;
  let mockToast: any;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockChannel = {
      on: jest.fn().mockReturnThis(),
      subscribe: jest.fn().mockReturnThis(),
    };

    mockSupabase = {
      channel: jest.fn().mockReturnValue(mockChannel),
      removeChannel: jest.fn(),
    };

    (createClient as jest.Mock).mockReturnValue(mockSupabase);
    (useAuthStore as unknown as jest.Mock).mockReturnValue({ user: mockUser });
    
    mockToast = jest.fn();
    (useToast as jest.Mock).mockReturnValue({ toast: mockToast });

    (api.get as jest.Mock).mockImplementation((url) => {
        if (url === '/notifications') return Promise.resolve({ data: [] });
        if (url === '/notifications/unread-count') return Promise.resolve({ data: { unread_count: 0 } });
        return Promise.resolve({ data: [] });
    });

    (api.patch as jest.Mock).mockResolvedValue({ data: { success: true } });
  });

  const triggerRealtimeNotification = async (notif: any) => {
    const callback = mockChannel.on.mock.calls.find((call: any) => call[0] === 'postgres_changes')[2];
    await act(async () => {
      callback({ new: notif });
    });
  };

  test('test_channel_subscribed_on_mount', async () => {
    await act(async () => {
        render(<NotificationBell />);
    });
    expect(mockSupabase.channel).toHaveBeenCalledWith('notifications');
  });

  test('test_postgres_changes_filter_correct', async () => {
    await act(async () => {
        render(<NotificationBell />);
    });
    expect(mockChannel.on).toHaveBeenCalledWith(
      'postgres_changes',
      {
        event: 'INSERT',
        table: 'notifications',
        filter: `user_id=eq.${mockUser.id}`,
      },
      expect.any(Function)
    );
  });

  test('test_subscribe_called', async () => {
    await act(async () => {
        render(<NotificationBell />);
    });
    expect(mockChannel.subscribe).toHaveBeenCalled();
  });

  test('test_new_notification_added_to_list', async () => {
    await act(async () => {
      render(<NotificationBell />);
    });
    
    const newNotif = {
      id: 'n1',
      type: 'signal',
      title: 'Realtime Noti',
      body: 'Body',
      created_at: new Date().toISOString(),
      is_read: false
    };
    
    await triggerRealtimeNotification(newNotif);

    fireEvent.click(screen.getByTestId('popover-trigger'));
    expect(screen.getByText('Realtime Noti')).toBeInTheDocument();
  });

  test('test_unread_count_increments_on_new', async () => {
    (api.get as jest.Mock).mockImplementation((url) => {
        if (url === '/notifications/unread-count') return Promise.resolve({ data: { unread_count: 3 } });
        return Promise.resolve({ data: [] });
    });

    await act(async () => {
      render(<NotificationBell />);
    });

    expect(screen.getByText('3')).toBeInTheDocument();

    const newNotif = {
      id: 'n1',
      type: 'signal',
      title: 'Noti 4',
      created_at: new Date().toISOString(),
      is_read: false
    };

    await triggerRealtimeNotification(newNotif);
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  test('test_toast_shown_on_new_notification', async () => {
    await act(async () => {
      render(<NotificationBell />);
    });
    
    const newNotif = {
      id: 'n1',
      type: 'signal',
      title: 'Toast Title',
      body: 'Toast Body',
      created_at: new Date().toISOString(),
      is_read: false
    };
    
    await triggerRealtimeNotification(newNotif);
    
    expect(mockToast).toHaveBeenCalledWith({
      type: 'signal',
      title: 'Toast Title',
      description: 'Toast Body',
    });
  });

  test('test_channel_removed_on_unmount', async () => {
    let unmount: any;
    await act(async () => {
        const res = render(<NotificationBell />);
        unmount = res.unmount;
    });
    unmount();
    expect(mockSupabase.removeChannel).toHaveBeenCalledWith(mockChannel);
  });

  test('test_signal_type_toast_cyan', async () => {
    await act(async () => {
      render(<NotificationBell />);
    });
    
    await triggerRealtimeNotification({
      id: 'n1',
      type: 'signal',
      title: 'Signal Noti',
      created_at: new Date().toISOString(),
      is_read: false
    });

    fireEvent.click(screen.getByTestId('popover-trigger'));
    
    const item = screen.getByText('Signal Noti').closest('.flex.gap-3');
    expect(item?.querySelector('.text-cyan-400')).toBeTruthy();
  });

  test('test_price_alert_type_toast_green', async () => {
    await act(async () => {
      render(<NotificationBell />);
    });
    
    await triggerRealtimeNotification({
      id: 'n1',
      type: 'price_alert',
      title: 'Price Noti',
      created_at: new Date().toISOString(),
      is_read: false
    });

    fireEvent.click(screen.getByTestId('popover-trigger'));
    const item = screen.getByText('Price Noti').closest('.flex.gap-3');
    expect(item?.querySelector('.text-green-400')).toBeTruthy();
  });

  test('test_system_type_toast_gray', async () => {
    await act(async () => {
      render(<NotificationBell />);
    });
    
    await triggerRealtimeNotification({
      id: 'n1',
      type: 'system',
      title: 'System Noti',
      created_at: new Date().toISOString(),
      is_read: false
    });

    fireEvent.click(screen.getByTestId('popover-trigger'));
    const item = screen.getByText('System Noti').closest('.flex.gap-3');
    expect(item?.querySelector('.text-gray-400')).toBeTruthy();
  });

  test('test_mark_all_read_resets_count', async () => {
    (api.get as jest.Mock).mockImplementation((url) => {
        if (url === '/notifications/unread-count') return Promise.resolve({ data: { unread_count: 5 } });
        return Promise.resolve({ data: [] });
    });

    await act(async () => {
      render(<NotificationBell />);
    });

    expect(screen.getByText('5')).toBeInTheDocument();
    
    fireEvent.click(screen.getByTestId('popover-trigger'));
    const markAllBtn = screen.getByText(/MARK ALL AS READ/i);
    
    await act(async () => {
        fireEvent.click(markAllBtn);
    });

    expect(api.patch).toHaveBeenCalledWith('/notifications/read-all');
    expect(screen.queryByText('5')).not.toBeInTheDocument();
  });

  test('test_mark_single_read_removes_highlight', async () => {
    (api.get as jest.Mock).mockImplementation((url) => {
        if (url === '/notifications') return Promise.resolve({ data: [{
            id: 'n1', title: 'Unread Noti', is_read: false, created_at: new Date().toISOString()
        }] });
        return Promise.resolve({ data: { unread_count: 1 } });
    });

    await act(async () => {
      render(<NotificationBell />);
    });

    fireEvent.click(screen.getByTestId('popover-trigger'));
    const item = screen.getByText('Unread Noti').closest('.p-4');
    expect(item).toHaveClass('bg-accent/5');

    await act(async () => {
        fireEvent.click(item!);
    });

    expect(api.patch).toHaveBeenCalledWith('/notifications/n1/read');
    expect(item).not.toHaveClass('bg-accent/5');
  });

  test('test_filter_tab_signals_only', async () => {
    (api.get as jest.Mock).mockImplementation((url) => {
        if (url === '/notifications') return Promise.resolve({ data: [
            { id: 'n1', type: 'signal', title: 'Signal 1', created_at: new Date().toISOString() },
            { id: 'n2', type: 'price_alert', title: 'Price 1', created_at: new Date().toISOString() }
        ] });
        return Promise.resolve({ data: { unread_count: 0 } });
    });

    await act(async () => {
      render(<NotificationBell />);
    });

    fireEvent.click(screen.getByTestId('popover-trigger'));
    expect(screen.getByText('Signal 1')).toBeInTheDocument();
    expect(screen.getByText('Price 1')).toBeInTheDocument();

    const signalsTab = screen.getByRole('tab', { name: /Signals/i });
    
    await act(async () => {
        fireEvent.click(signalsTab);
    });

    expect(screen.getByText('Signal 1')).toBeInTheDocument();
    expect(screen.queryByText('Price 1')).not.toBeInTheDocument();
  });

  test('test_empty_state_shown', async () => {
    await act(async () => {
        render(<NotificationBell />);
    });
    
    fireEvent.click(screen.getByTestId('popover-trigger'));
    expect(screen.getByText(/No notifications here/i)).toBeInTheDocument();
  });

  test('test_9plus_badge', async () => {
    (api.get as jest.Mock).mockImplementation((url) => {
        if (url === '/notifications/unread-count') return Promise.resolve({ data: { unread_count: 15 } });
        return Promise.resolve({ data: [] });
    });

    await act(async () => {
      render(<NotificationBell />);
    });

    expect(screen.getByText('9+')).toBeInTheDocument();
  });

  test('test_badge_hidden_at_zero', async () => {
    (api.get as jest.Mock).mockImplementation((url) => {
        if (url === '/notifications/unread-count') return Promise.resolve({ data: { unread_count: 0 } });
        return Promise.resolve({ data: [] });
    });

    await act(async () => {
      render(<NotificationBell />);
    });

    const trigger = screen.getByTestId('popover-trigger');
    expect(trigger.querySelector('span')).not.toBeInTheDocument();
  });

  test('test_dropdown_closes_on_outside_click', async () => {
    await act(async () => {
      render(<NotificationBell />);
    });

    const trigger = screen.getByTestId('popover-trigger');
    
    // Open
    await act(async () => {
        fireEvent.click(trigger);
    });
    expect(screen.getByTestId('popover-portal')).toBeInTheDocument();

    // Close
    await act(async () => {
        fireEvent.click(trigger);
    });
    expect(screen.queryByTestId('popover-portal')).not.toBeInTheDocument();
  });
});

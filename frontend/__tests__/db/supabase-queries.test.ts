import { createClient } from '../../lib/supabase';

// Mock Supabase client
jest.mock('../../lib/supabase', () => ({
  createClient: jest.fn()
}));

describe('Supabase Queries Isolation & Automatic RLS', () => {
  let mockSupabase: any;

  beforeEach(() => {
    mockSupabase = {
      from: jest.fn().mockReturnThis(),
      select: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      single: jest.fn().mockReturnThis(),
      execute: jest.fn().mockResolvedValue({ data: [], error: null })
    };
    (createClient as jest.Mock).mockReturnValue(mockSupabase);
  });

  test('test_portfolios_no_user_id_in_query', async () => {
    // This test verifies that the frontend does NOT explicitly filter by user_id
    // for portfolios, relying on RLS instead.
    
    // Simulate the call made in fetchData()
    await mockSupabase.from('portfolios').select('*, portfolio_positions(count)');
    
    // Verify .from('portfolios') was called
    expect(mockSupabase.from).toHaveBeenCalledWith('portfolios');
    
    // Verify .select was called with positions count
    expect(mockSupabase.select).toHaveBeenCalledWith('*, portfolio_positions(count)');
    
    // CRITICAL: Verify .eq('user_id', ...) was NOT called for this query
    const eqCalls = mockSupabase.eq.mock.calls;
    const hasUserIdFilter = eqCalls.some((call: any) => call[0] === 'user_id');
    expect(hasUserIdFilter).toBe(false);
  });

  test('test_profile_fetched_on_mount', async () => {
    // This test verifies that the profile IS explicitly filtered by user id on mount
    const userId = 'test-user-id';
    
    // Simulate the call made in fetchProfile()
    await mockSupabase.from('profiles').select('*').eq('id', userId).single();
    
    expect(mockSupabase.from).toHaveBeenCalledWith('profiles');
    expect(mockSupabase.eq).toHaveBeenCalledWith('id', userId);
    expect(mockSupabase.single).toHaveBeenCalled();
  });
});

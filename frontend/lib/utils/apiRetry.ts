/**
 * Wrapper for fetch API with exponential backoff and timeout handling.
 * Ensures the frontend does not crash if the backend is temporarily down.
 */

interface FetchRetryOptions extends RequestInit {
    maxRetries?: number;
    baseDelayMs?: number;
    timeoutMs?: number;
}

export async function fetchWithRetry(url: string, options: FetchRetryOptions = {}): Promise<Response> {
    const {
        maxRetries = 3,
        baseDelayMs = 1000,
        timeoutMs = 10000,
        ...fetchOptions
    } = options;

    let attempt = 0;

    while (attempt <= maxRetries) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const response = await fetch(url, {
                ...fetchOptions,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            // If successful or it's a client error (4xx), return the response immediately
            // We usually only want to retry on 5xx errors or network failures
            if (response.ok || (response.status >= 400 && response.status < 500)) {
                return response;
            }

            throw new Error(`HTTP Error: ${response.status}`);
        } catch (error) {
            clearTimeout(timeoutId);
            
            const isAbortError = error instanceof Error && error.name === 'AbortError';
            
            if (attempt === maxRetries) {
                if (isAbortError) {
                    throw new Error('Request Timeout');
                }
                throw error;
            }

            // Exponential backoff
            const delay = baseDelayMs * Math.pow(2, attempt);
            await new Promise((resolve) => setTimeout(resolve, delay));
            attempt++;
        }
    }

    throw new Error('Max retries reached');
}

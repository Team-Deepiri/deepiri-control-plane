/**
 * Shared Utilities for Deepiri Microservices
 * Export all shared utilities from this module
 */

import { createLogger } from './logger';
import winston from 'winston';

export { createLogger };
export const logger: winston.Logger = createLogger('shared-utils');

// Streaming
export { StreamingClient, StreamTopics } from './streaming/StreamingClient';
export type { StreamEvent } from './streaming/StreamingClient';

// Secure logging
export { secureLog } from './secureLogger';

// Config / Secret validation
export { validateSecret, validateDatabaseUrl } from './config/secrets';

export {
  SecretValidator,
  createSecretValidator,
  PasswordValidator,
  ApiKeyValidator,
  TokenValidator,
  UrlValidator,
  EnvironmentType,
  SecretType,
} from './config';

export type {
  SecretConfig,
  ValidationResult,
  ValidationError,
} from './config';

// Auth & Cache Utilities
export { hashApiKey } from './cryptoUtils';
export { createRedisClient } from './redisClient';

export type { ApiKeyScope, ApiKeyCachePayload } from './types';
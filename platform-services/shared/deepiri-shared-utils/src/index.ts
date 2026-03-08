/**
 * Shared Utilities for Deepiri Microservices
 * Export all shared utilities from this module
 */
import { createLogger, secureLog } from './logger';
import winston from 'winston';

export { createLogger, secureLog };
export const logger: winston.Logger = createLogger('shared-utils'); // Default logger instance
export { StreamingClient, StreamTopics } from './streaming/StreamingClient';
export type { StreamEvent } from './streaming/StreamingClient';


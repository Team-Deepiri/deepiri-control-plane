import express, { Express, Request, Response, ErrorRequestHandler } from 'express';
// MongoDB removed - analytics uses InfluxDB for time-series and PostgreSQL for metadata
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { secureLog } from '@deepiri/shared-utils';
import routes from './index';
<<<<<<< Updated upstream
=======
import { validateBodyIfPresent } from './middleware/inputValidation';
import { bodyParserConfig, requestSizeLimiter } from './middleware/requestLimits';
>>>>>>> Stashed changes

dotenv.config();

const app: Express = express();
const PORT: number = parseInt(process.env.PORT || '5004', 10);

app.use(helmet());
app.use(cors());
<<<<<<< Updated upstream
app.use(express.json());
=======

// Request size limits (Issue 8)
app.use(requestSizeLimiter);
app.use(express.json(bodyParserConfig.json));
app.use(express.urlencoded(bodyParserConfig.urlencoded));
app.use(validateBodyIfPresent());
>>>>>>> Stashed changes

// PostgreSQL connection via Prisma (if needed for analytics metadata)
// Primary analytics data stored in InfluxDB

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'platform-analytics-service', timestamp: new Date().toISOString() });
});

app.use('/', routes);

const errorHandler: ErrorRequestHandler = (err, req, res, next) => {
  secureLog('error', 'Platform Analytics Service error:', err);
  res.status(500).json({ error: 'Internal server error' });
};
app.use(errorHandler);

// Start event consumption
import { startEventConsumption } from './streaming/eventConsumer';

startEventConsumption().catch((err) => {
  secureLog('error', 'Failed to start event consumption:', err);
});

app.listen(PORT, () => {
  secureLog('info', `Platform Analytics Service running on port ${PORT}`);
});

export default app;


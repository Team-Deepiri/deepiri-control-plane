import express, { Express, Request, Response, ErrorRequestHandler } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { secureLog } from '@deepiri/shared-utils';
import routes from './index';
import { connectDatabase } from './db';
<<<<<<< Updated upstream
=======
import { validateBodyIfPresent } from './middleware/inputValidation';
import { bodyParserConfig, requestSizeLimiter } from './middleware/requestLimits';
>>>>>>> Stashed changes

dotenv.config();

const app: Express = express();
const PORT: number = parseInt(process.env.PORT || '5003', 10);

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

// PostgreSQL connection via Prisma
connectDatabase()
  .catch((err: Error) => {
    secureLog('error', 'Engagement Service: Failed to connect to PostgreSQL', err);
    process.exit(1);
  });

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'engagement-service', timestamp: new Date().toISOString() });
});

app.use('/', routes);

const errorHandler: ErrorRequestHandler = (err, req, res, next) => {
  secureLog('error', 'Engagement Service error:', err);
  res.status(500).json({ error: 'Internal server error' });
};
app.use(errorHandler);

app.listen(PORT, () => {
  secureLog('info', `Engagement Service running on port ${PORT}`);
});

export default app;


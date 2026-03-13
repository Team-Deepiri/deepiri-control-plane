import express, { Express, Request, Response, ErrorRequestHandler } from 'express';
// MongoDB removed - challenge service uses Cyrex API
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { secureLog } from '@deepiri/shared-utils';
import axios from 'axios';
import { bodyParserConfig, requestSizeLimiter } from './middleware/requestLimits';

dotenv.config();

const app: Express = express();
const PORT: number = parseInt(process.env.PORT || '5007', 10);

app.use(helmet());
app.use(cors());

// Request size limits (Issue 8)
app.use(requestSizeLimiter);
app.use(express.json(bodyParserConfig.json));
app.use(express.urlencoded(bodyParserConfig.urlencoded));

// PostgreSQL connection via Prisma (if needed for challenge storage)
// For now, challenges are generated via Cyrex API

const CYREX_URL: string = process.env.CYREX_URL || 'http://cyrex:8000';

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: 'challenge-service', timestamp: new Date().toISOString() });
});

app.post('/generate', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(`${CYREX_URL}/agent/challenge/generate`, req.body);
    res.json(response.data);
  } catch (error: any) {
    secureLog('error', 'Challenge generation error:', error);
    res.status(500).json({ error: 'Failed to generate challenge' });
  }
});

const errorHandler: ErrorRequestHandler = (err, req, res, next) => {
  secureLog('error', 'Challenge Service error:', err);
  res.status(500).json({ error: 'Internal server error' });
};
app.use(errorHandler);

app.listen(PORT, () => {
  secureLog('info', `Challenge Service running on port ${PORT}`);
});

export default app;


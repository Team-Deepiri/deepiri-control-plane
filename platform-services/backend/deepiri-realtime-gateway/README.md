# Realtime Gateway

Handles real-time communication and WebSocket connections.

## Responsibilities
- WebSocket server
- Real-time challenge updates
- Multiplayer sessions
- Presence tracking

## Events
- `connection` - Client connects
- `join_user_room` - Join user-specific room
- `join_adventure_room` - Join adventure room
- `challenge-update` - Challenge progress update
- `notification` - New notification

## Current Implementation
See `deepiri-core-api/server.js` for Socket.IO setup.

## Migration
Extract WebSocket functionality to this independent service.

## Streaming Flags
- `SYNAPSE_SUGAR_GLIDER_URL` sets the Sugar Glider base URL (preferred).
- `SYNAPSE_SIDECAR_URL` remains supported as a legacy fallback (default fallback target: `http://synapse-sidecar:8081`).
- `STREAM_CONSUMER_GROUP` sets the transport consumer group (default: `realtime-gateway`).
- `STREAM_CONSUMER_NAME` sets the transport consumer name (default: `realtime-1`).

Realtime Gateway now consumes streams via Sugar Glider (formerly sidecar). Redis remains part of the design, but only behind the transport service.


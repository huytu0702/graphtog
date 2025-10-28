frontend log:
Auth error: TypeError: fetch failed

    at node:internal/deps/undici/undici:12637:11

    at process.processTicksAndRejections (node:internal/process/task_queues:95:5)

    at async Object.authorize (/app/.next/server/app/page.js:1:3718)

    at async Object.c (/app/.next/server/chunks/790.js:30:4502)

    at async m (/app/.next/server/chunks/790.js:6:15891)

    at async a (/app/.next/server/chunks/790.js:30:19768)

    at async e.length.t (/app/.next/server/chunks/790.js:30:21258)

    at async /app/node_modules/next/dist/compiled/next-server/app-route.runtime.prod.js:6:36258

    at async eR.execute (/app/node_modules/next/dist/compiled/next-server/app-route.runtime.prod.js:6:26874)

    at async eR.handle (/app/node_modules/next/dist/compiled/next-server/app-route.runtime.prod.js:6:37512) {

  cause: Error: connect ECONNREFUSED ::1:8000

      at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1555:16)

      at TCPConnectWrap.callbackTrampoline (node:internal/async_hooks:128:17) {

    errno: -111,

    code: 'ECONNREFUSED',

    syscall: 'connect',

    address: '::1',

    port: 8000

  }

}

backend log:
INFO:     Started server process [1]

INFO:     Waiting for application startup.

INFO:app.main:🚀 Starting GraphToG application...

INFO:app.main:✅ PostgreSQL database initialized

✅ Neo4j schema initialized successfully

INFO:app.main:✅ Neo4j graph database initialized

INFO:app.services.graph_service:Created constraint: CREATE CONSTRAINT entity_name_type IF NOT EXISTS F...

INFO:app.services.graph_service:Created constraint: CREATE CONSTRAINT textunit_id IF NOT EXISTS FOR (t...

INFO:app.services.graph_service:Created constraint: CREATE CONSTRAINT community_id IF NOT EXISTS FOR (...

INFO:app.services.graph_service:Created index: CREATE INDEX entity_type IF NOT EXISTS FOR (e:Enti...

INFO:app.services.graph_service:Created index: CREATE INDEX textunit_doc_id IF NOT EXISTS FOR (t:...

INFO:app.services.graph_service:Created index: CREATE INDEX entity_confidence IF NOT EXISTS FOR (...

INFO:app.services.graph_service:Created index: CREATE INDEX relationship_type IF NOT EXISTS FOR (...

INFO:app.services.graph_service:✅ Graph schema initialized

INFO:app.main:✅ Graph schema initialized

INFO:     Application startup complete.

INFO:     Uvicorn running on http://0.0.0.0:8000⁠ (Press CTRL+C to quit)

INFO:     127.0.0.1:57340 - "GET /health HTTP/1.1" 200 OK

INFO:     127.0.0.1:58618 - "GET /health HTTP/1.1" 200 OK

INFO:     172.18.0.1:51388 - "OPTIONS /api/auth/register HTTP/1.1" 200 OK

INFO:     172.18.0.1:51388 - "POST /api/auth/register HTTP/1.1" 200 OK

INFO:     127.0.0.1:41238 - "GET /health HTTP/1.1" 200 OK

INFO:     127.0.0.1:46482 - "GET /health HTTP/1.1" 200 OK
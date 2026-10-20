# Trajectory website

Next.js app for Trajectory. It calls the API in `../api`.

```bash
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL
npm install
npm run dev                  # http://localhost:3000
npm run lint                 # Biome
npm run build
```

Pages:

- `/` job finder: resume upload, filters, ranked jobs, skills to learn.
- `/courses` course search.
- `/courses/[id]` one course with its prerequisite graph.

See the main README for deploy steps.

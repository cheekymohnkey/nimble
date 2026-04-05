# Dungeon Master Assistant - Technical Approach

## Project Vision

Build a Dungeon Master Assistant for tabletop RPGs with two complementary brains:

- **Rules brain**: deterministic combat engine, initiative tracking, encounter state, conditions, inventory management
- **Story brain**: LLM-driven narration, NPC roleplay, session summarization, continuity stitching

This split keeps the core engine reliable while letting a language model handle storytelling and roleplaying.

A character generator will also be included as a player-facing tool for building and customizing characters, with generated archetypes, stats, and narrative hooks.

## Recommended Stack

### Backend
- **FastAPI**
- **SQLAlchemy 2.x**
- **SQLite** to start

Why FastAPI fits:
- Lightweight and fast to build
- Strong typed request/response model support
- Excellent integration with Python-based AI tooling
- Keeps the deterministic engine clean and focused

Why SQLAlchemy + SQLite fits:
- SQLite is ideal for early-stage solo or small-group tools
- Campaigns, NPCs, encounters, session notes, and combat snapshots are easy to model
- SQLAlchemy supports SQLite out of the box and scales to more advanced databases later

### Frontend
- **React + Next.js (TypeScript)**
- **TanStack Query** for data fetching and cache management

Why Next.js is a good frontend choice:
- Polished app shell with room for hybrid rendering or SSR later
- Built-in TypeScript support
- Good path for future auth, session sharing, or hosted campaign pages
- Easy API integration with FastAPI

Why TanStack Query works:
- Simplifies syncing frontend state with backend data
- Avoids manual cache management for campaigns, encounters, combat logs, and story beats
- Ideal for a dashboard-style DM console

## Why Python Wins Here

Python is a strong match for the storytelling/AI orchestration side:

- LLM tooling, prompt pipelines, JSON shaping, and content validation are natural in Python
- FastAPI keeps the rules engine separate from narrative generation
- The deterministic combat engine can stay framework-light while the story brain uses Python’s AI ecosystem

### Mental Model
- Python for the engine and AI orchestration
- React/Next.js for the DM-facing UI

## When Node.js/NestJS Is a Better Fit

Choose Node.js with NestJS if:
- You want TypeScript across backend and frontend
- You prefer a more structured, enterprise-style backend from the start
- You want one language across the full stack

Suggested Node stack:
- **Backend**: NestJS
- **ORM**: Prisma
- **Database**: SQLite
- **Frontend**: Next.js

NestJS has strong Prisma guidance and good SQLite support, but for this exact use case Python often feels more elegant unless the team already prefers TypeScript.

## Recommended Path

For this project, the best match is:
- **Backend**: FastAPI + SQLAlchemy 2.x + SQLite
- **Frontend**: Next.js + React + TypeScript
- **UI/data layer**: TanStack Query

This combination gives a clean separation between deterministic game logic and generative story/roleplay, while keeping the frontend state syncing simple and scalable.

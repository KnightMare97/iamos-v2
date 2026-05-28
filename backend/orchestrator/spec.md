# Orchestrator

## Responsibility
The central nervous system of IAMOS. Listens to all events and decides what happens next. Only the orchestrator may trigger state transitions and create/update domain records.

## Core Principle
Agents propose. The orchestrator decides. No domain service, no AI agent, no worker may mutate state directly. All state changes flow through the orchestrator.

## What It Does
- Subscribes to all events on the Redis Streams event bus
- Evaluates current state of affected aggregate
- Decides next action based on state machine definitions
- Calls domain services to execute transitions
- Logs every decision as an event

## Event Handling Pattern
For each incoming event:
1. Identify aggregate (aggregate_id + aggregate_type)
2. Load current state from Postgres
3. Look up valid transitions for current state + event type
4. Check guard conditions
5. Execute transition via domain service
6. Emit resulting event

## Failure Handling
- If a transition fails: log error, emit system.error event, do not retry automatically — require human review
- If an event cannot be routed: log as unhandled, alert operator
- Orchestrator itself must be stateless — all state is in Postgres

## Modules
- engine.py — main event loop and routing logic
- Each domain has a handler registered in the engine

## Rules
- Orchestrator never calls Claude API directly
- Orchestrator never reads from one domain's tables on behalf of another
- Every decision is logged
- Orchestrator is the only writer to state fields on aggregates

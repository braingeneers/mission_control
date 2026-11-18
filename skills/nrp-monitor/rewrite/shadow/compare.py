"""Pure decision extraction and delayed comparison; never compare final states."""
import re


def category(message):
    if 'NRP band violation safety stop:' in message:
        return 'safety_stop'
    if re.match(r'stage \S+ waits on ', message):
        return 'wait'
    if 'utilization restart stage ' in message:
        return 'restart'
    if message.startswith('submitted '):
        return 'submit'
    if 'agent start' in message:
        return 'fix_agent'
    if message.startswith('utilization review'):
        return 'utilization_review'
    if re.match(r'stage \S+ FAILED', message):
        return 'mark_failed'
    if re.match(r'stage \S+ done', message) or message.startswith('DONE'):
        return 'mark_done'
    if message.startswith('WITH_COORDINATOR'):
        return 'coordinator'
    return None


def stage_for(message, task, context=None):
    for stage in task['stages']:
        if re.search(r'(?<![\w-])' + re.escape(stage['id']) + r'(?![\w-])', message) or stage.get('job', '\0') in message:
            return stage['id']
    active = [s['id'] for s in task['stages'] if s['state'] != 'done']
    return context or (active[0] if len(active) == 1 else None)


def installed_events(lines, tasks):
    events, context, utilization = [], {}, {}
    for index, line in enumerate(lines):
        match = re.match(r'(.{19}) task ([^:]+): (.*)', line)
        if not match:
            continue
        time, name, message = match.groups()
        if name not in tasks:
            continue
        stage = stage_for(message, tasks[name], context.get(name))
        if message.startswith('utilization observation'):
            utilization[name] = True
            if stage:
                context[name] = stage
            continue  # Measurement, not a decision to start a review.
        kind = category(message)
        if not kind:
            continue
        if kind == 'mark_failed':
            utilization[name] = False
        if kind == 'fix_agent' and utilization.get(name, bool(tasks[name].get('util_event'))):
            kind = 'utilization_review'
        if stage:
            context[name] = stage
            events.append(dict(time=time, task=name, stage=stage, category=kind,
                               evidence=f'monitor.log line {index + 1}: {kind}'))
    return events


def shadow_decisions(actions, tasks):
    """The first suppressed effect ends reliable task coverage for this pass.

    Earlier decisions remain valid. Later events are listed as provisional, never
    assigned to untouched sibling stages as if they had been observed.
    """
    first, cut, provisional = {}, set(), []
    for index, action in enumerate(actions):
        name = action.get('task')
        if name not in tasks:
            continue
        route = action['would_do']
        message = action.get('message', '')
        if message.startswith(f'task {name}: '):
            message = message.split(': ', 1)[1]
        kind = action.get('category') if route == 'decision' else category(message) if route == 'observation' else None
        stage = action.get('stage') or stage_for(message, tasks[name])
        suppressed = route not in ('decision', 'observation')
        if name in cut:
            provisional.append(dict(task=name, route=route, category=kind, stage=stage, index=index))
            continue
        if suppressed and not kind:
            kind = {'kubectl apply': 'submit', 'agents.dispatch_agent': 'fix_agent'}.get(route)
            if route.startswith('filesystem write'):
                kind = 'suppressed_write'
        if stage and kind:
            first.setdefault((name, stage), dict(category=kind, evidence=f'shadow-actions.jsonl row {index + 1}: {route}', time=action['time']))
        if suppressed:
            cut.add(name)
    rows = []
    for name, task in tasks.items():
        for stage in task['stages']:
            decision = first.get((name, stage['id']))
            rows.append(dict(task=name, stage=stage['id'], **(decision or dict(
                category='unobserved' if name in cut else 'wait', evidence='after suppression' if name in cut else 'no action reached in pass'))))
    return rows, provisional


def judge(row, events, now):
    """No matching evidence yet is pending; expiry without evidence is unknown.

    A conflicting FIRST installed decision is unexplained, even if a later one
    matches. This prevents selecting a convenient later ladder outcome.
    """
    candidates = [e for e in events if e['task'] == row['task'] and e['stage'] == row['stage']
                  and row['start'] <= e['time'] <= row['deadline']]
    if row['category'] in ('unobserved', 'suppressed_write'):
        return dict(row, verdict='unknown', installed='shadow coverage suppressed')
    if candidates:
        event = min(candidates, key=lambda e: e['time'])
        return dict(row, verdict='matched' if event['category'] == row['category'] else 'unexplained',
                    installed=event['evidence'], installed_category=event['category'])
    return dict(row, verdict='pending' if now < row['deadline'] else 'unknown', installed='no installed decision recorded in window')

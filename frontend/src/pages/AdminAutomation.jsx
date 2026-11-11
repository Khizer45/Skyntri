import { Copy, Play, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import Button from '../components/Button.jsx'
import Card from '../components/Card.jsx'
import Modal from '../components/Modal.jsx'
import { Alert, Badge, Empty, Field, Section, StatusBadge, Tabs, dateTime } from '../components/ui.jsx'
import { useToast } from '../context/ToastContext.jsx'
import AdminLayout from '../layouts/AdminLayout.jsx'
import * as api from '../services/api.js'

function CopyField({ value, label }) {
  const { showToast } = useToast()
  return (
    <div>
      <span className="label">{label}</span>
      <div className="flex gap-2">
        <input className="field font-mono text-xs" readOnly value={value} onFocus={(e) => e.target.select()} />
        <Button variant="outline" icon={Copy} aria-label={`Copy ${label}`} onClick={() => navigator.clipboard.writeText(value).then(() => showToast('Copied.', 'success'))} />
      </div>
    </div>
  )
}

// ----------------------------------------------------------------- agents

function Agents({ data, reload }) {
  const { showToast } = useToast()
  const [busy, setBusy] = useState('')

  const run = async (name) => {
    setBusy(name)
    try {
      const result = await api.adminRunAgent(name)
      showToast(result.summary || 'Agent finished.', result.status === 'ok' ? 'success' : 'error')
      reload()
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="space-y-8">
      <Section
        title="Agents"
        description={
          data.scheduler_enabled
            ? `Run by the server: reminders every hour, report and post daily at ${String(data.daily_hour).padStart(2, '0')}:00 (${data.timezone}).`
            : 'The built-in scheduler is off. Start agents here, from n8n, or set AGENTS_SCHEDULER_ENABLED=true on the server.'
        }
      >
        <Card className="divide-soft">
          {data.agents.map((agent) => (
            <div key={agent.name} className="flex items-center justify-between gap-3 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-neutral-900 dark:text-white">{agent.label}</p>
                <p className="muted font-mono text-xs">{agent.name}</p>
              </div>
              <Button size="sm" variant="outline" icon={Play} loading={busy === agent.name} onClick={() => run(agent.name)}>Run now</Button>
            </div>
          ))}
        </Card>
      </Section>

      <Section title="Recent runs">
        {data.runs.length === 0 ? (
          <p className="muted text-sm">No agent has run yet.</p>
        ) : (
          <Card className="divide-soft">
            {data.runs.map((run_) => (
              <div key={run_.id} className="px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-neutral-900 dark:text-white">{run_.label} <StatusBadge status={run_.status} /></p>
                  <p className="muted text-xs">{dateTime(run_.started_at)} · {run_.triggered_by.split(':')[0]}</p>
                </div>
                {run_.summary && <p className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">{run_.summary}</p>}
              </div>
            ))}
          </Card>
        )}
      </Section>
    </div>
  )
}

// ------------------------------------------------------------------ posts

function Posts() {
  const { showToast } = useToast()
  const [posts, setPosts] = useState(null)
  const [form, setForm] = useState(null)

  const load = useCallback(() => api.adminListPosts().then(setPosts).catch(() => setPosts([])), [])
  useEffect(() => {
    load()
  }, [load])

  const act = async (action) => {
    try {
      await action()
      load()
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  const save = async (e) => {
    e.preventDefault()
    await act(async () => {
      if (form.id) await api.adminUpdatePost(form.id, { title: form.title, body: form.body })
      else await api.adminCreatePost({ title: form.title, body: form.body, kind: form.kind, publish: false })
      setForm(null)
    })
  }

  return (
    <Section
      title="Clinic posts"
      description="Shown to signed-in users on Home. The daily post agent adds drafts here. Publishing also sends a post.published event to your webhooks."
      action={<Button size="sm" icon={Plus} onClick={() => setForm({ title: '', body: '', kind: 'announcement' })}>New post</Button>}
    >
      {posts === null ? (
        <p className="muted text-sm">Loading…</p>
      ) : posts.length === 0 ? (
        <Empty title="No posts yet" />
      ) : (
        <div className="space-y-3">
          {posts.map((post) => (
            <Card key={post.id} className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-sm font-semibold text-neutral-900 dark:text-white">{post.title} <StatusBadge status={post.status} /> <Badge>{post.source}</Badge></p>
                <div className="flex gap-1.5">
                  {post.status === 'draft' ? (
                    <Button size="sm" onClick={() => act(() => api.adminUpdatePost(post.id, { publish: true }))}>Publish</Button>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => act(() => api.adminUpdatePost(post.id, { publish: false }))}>Unpublish</Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => setForm(post)}>Edit</Button>
                  <Button size="sm" variant="ghost" icon={Trash2} aria-label="Delete post" onClick={() => window.confirm('Delete this post?') && act(() => api.adminDeletePost(post.id))} />
                </div>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-neutral-700 dark:text-neutral-300">{post.body}</p>
            </Card>
          ))}
        </div>
      )}

      <Modal open={Boolean(form)} onClose={() => setForm(null)} title={form?.id ? 'Edit post' : 'New post'} wide>
        {form && (
          <form onSubmit={save} className="space-y-4">
            <Field label="Title"><input className="field" required minLength={3} maxLength={140} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <Field label="Text" hint="Markdown is supported."><textarea className="field" rows={8} required minLength={10} maxLength={5000} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></Field>
            <Button type="submit">Save as {form.id ? 'is' : 'draft'}</Button>
          </form>
        )}
      </Modal>
    </Section>
  )
}

// --------------------------------------------------------------- webhooks

function Webhooks({ data, reload }) {
  const { showToast } = useToast()
  const [form, setForm] = useState(null)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const eventNames = Object.keys(data.events).filter((e) => e !== 'test.ping')

  const open = async (id) => {
    try {
      setDetail(await api.adminGetWebhook(id))
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  const save = async (e) => {
    e.preventDefault()
    setError('')
    const payload = {
      name: form.name, url: form.url, include_contact: form.include_contact, is_active: form.is_active,
      events: form.all ? ['*'] : form.events,
    }
    try {
      const saved = form.id ? await api.adminUpdateWebhook(form.id, payload) : await api.adminCreateWebhook(payload)
      setForm(null)
      setDetail({ ...saved, deliveries: [] })
      reload()
    } catch (err) {
      setError(err.message)
    }
  }

  const test = async () => {
    try {
      const result = await api.adminTestWebhook(detail.id)
      showToast(result.ok ? 'Test event delivered.' : `Delivery failed: ${result.error}`, result.ok ? 'success' : 'error')
      open(detail.id)
      reload()
    } catch (err) {
      showToast(err.message, 'error')
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete this webhook?')) return
    await api.adminDeleteWebhook(detail.id).catch((err) => showToast(err.message, 'error'))
    setDetail(null)
    reload()
  }

  const edit = (hook) =>
    setForm({ ...hook, all: hook.events.includes('*'), events: hook.events.filter((e) => e !== '*') })

  return (
    <Section
      title="Webhooks"
      description="Skyntri sends a signed message to these addresses when something happens. Paste the webhook URL from n8n, Zapier or Make."
      action={<Button size="sm" icon={Plus} onClick={() => { setError(''); setForm({ name: '', url: '', all: true, events: [], include_contact: false, is_active: true }) }}>Add webhook</Button>}
    >
      {data.webhooks.length === 0 ? (
        <Empty title="No webhooks yet" />
      ) : (
        <Card className="divide-soft">
          {data.webhooks.map((hook) => (
            <button key={hook.id} onClick={() => open(hook.id)} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-neutral-900/[0.03] dark:hover:bg-white/5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-neutral-900 dark:text-white">{hook.name}</p>
                <p className="muted truncate font-mono text-xs">{hook.url}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                {hook.include_contact && <Badge tone="amber">Contact details</Badge>}
                {!hook.is_active ? <Badge tone="red">Off</Badge> : hook.last_status && <Badge tone={hook.last_status === 'ok' ? 'green' : 'red'}>{hook.last_status === 'ok' ? 'OK' : 'Failing'}</Badge>}
              </div>
            </button>
          ))}
        </Card>
      )}

      <Modal open={Boolean(form)} onClose={() => setForm(null)} title={form?.id ? 'Edit webhook' : 'Add webhook'} wide>
        {form && (
          <form onSubmit={save} className="space-y-4">
            <Field label="Name"><input className="field" required minLength={2} maxLength={80} placeholder="n8n reminders" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="URL" hint="Must be an https:// address that is reachable from the internet.">
              <input className="field font-mono text-xs" required type="url" placeholder="https://your-n8n.example.com/webhook/skyntri" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
            </Field>
            <div>
              <span className="label">Events</span>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.all} onChange={(e) => setForm({ ...form, all: e.target.checked })} /> All events</label>
              {!form.all && (
                <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {eventNames.map((name) => (
                    <label key={name} className="flex items-start gap-2 text-sm">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={form.events.includes(name)}
                        onChange={(e) => setForm({ ...form, events: e.target.checked ? [...form.events, name] : form.events.filter((x) => x !== name) })}
                      />
                      <span><span className="font-mono text-xs">{name}</span><span className="muted block text-xs">{data.events[name]}</span></span>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={form.include_contact} onChange={(e) => setForm({ ...form, include_contact: e.target.checked })} />
              <span>Include the patient's name, e-mail and phone in appointment events<span className="muted block text-xs">Needed for reminder messages. Turn on only for a service you trust: this is personal data leaving Skyntri. Reasons for a visit and medical notes are never sent.</span></span>
            </label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Active</label>
            {error && <Alert>{error}</Alert>}
            <Button type="submit">Save</Button>
          </form>
        )}
      </Modal>

      <Modal open={Boolean(detail)} onClose={() => setDetail(null)} title={detail?.name || 'Webhook'} wide>
        {detail && (
          <div className="space-y-4">
            <CopyField label="Signing secret" value={detail.secret} />
            <p className="muted text-xs">
              Every request has the header <span className="font-mono">X-Skyntri-Signature: sha256=…</span>, the HMAC-SHA256 of
              <span className="font-mono"> timestamp + "." + body</span> with this secret. Check it in your workflow to be sure the message is from Skyntri.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={test}>Send test event</Button>
              <Button size="sm" variant="outline" onClick={() => { setError(''); edit(detail); setDetail(null) }}>Edit</Button>
              <Button size="sm" variant="ghost" icon={Trash2} onClick={remove}>Delete</Button>
            </div>
            <div>
              <span className="label">Last deliveries</span>
              {detail.deliveries.length === 0 ? <p className="muted text-sm">Nothing sent yet.</p> : (
                <div className="divide-soft rounded-lg border border-neutral-200 dark:border-white/10">
                  {detail.deliveries.map((d) => (
                    <div key={d.id} className="flex items-center justify-between gap-2 px-3 py-2 text-xs">
                      <span className="font-mono">{d.event}</span>
                      <span className="muted">{dateTime(d.created_at)}</span>
                      <Badge tone={d.ok ? 'green' : 'red'}>{d.ok ? `OK ${d.status_code}` : d.error || 'Failed'}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </Section>
  )
}

// --------------------------------------------------------------- API keys

function ApiKeys({ data, reload }) {
  const { showToast } = useToast()
  const [form, setForm] = useState(null)
  const [created, setCreated] = useState(null)
  const [error, setError] = useState('')

  const create = async (e) => {
    e.preventDefault()
    setError('')
    try {
      setCreated(await api.adminCreateApiKey(form.name, form.scopes))
      setForm(null)
      reload()
    } catch (err) {
      setError(err.message)
    }
  }

  const revoke = async (key) => {
    if (!window.confirm(`Revoke "${key.name}"? Tools using it stop working at once.`)) return
    await api.adminRevokeApiKey(key.id).catch((err) => showToast(err.message, 'error'))
    reload()
  }

  return (
    <Section
      title="API keys"
      description="For tools that call Skyntri: n8n, Zapier or your own agent. Send the key in the X-API-Key header to /automation/v1/…"
      action={<Button size="sm" icon={Plus} onClick={() => { setError(''); setForm({ name: '', scopes: ['read:summary'] }) }}>New key</Button>}
    >
      {data.api_keys.length === 0 ? (
        <Empty title="No API keys yet" />
      ) : (
        <Card className="divide-soft">
          {data.api_keys.map((key) => (
            <div key={key.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-neutral-900 dark:text-white">{key.name} {key.revoked && <Badge tone="red">Revoked</Badge>}</p>
                <p className="muted font-mono text-xs">{key.prefix}… · {key.scopes.join(', ')}</p>
                <p className="muted text-xs">{key.last_used_at ? `Last used ${dateTime(key.last_used_at)}` : 'Never used'}</p>
              </div>
              {!key.revoked && <Button size="sm" variant="outline" onClick={() => revoke(key)}>Revoke</Button>}
            </div>
          ))}
        </Card>
      )}

      <Modal open={Boolean(form)} onClose={() => setForm(null)} title="New API key">
        {form && (
          <form onSubmit={create} className="space-y-4">
            <Field label="Name"><input className="field" required minLength={2} maxLength={80} placeholder="n8n" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div>
              <span className="label">What may this key do?</span>
              <div className="space-y-1.5">
                {Object.entries(data.scopes).map(([scope, text]) => (
                  <label key={scope} className="flex items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={form.scopes.includes(scope)}
                      onChange={(e) => setForm({ ...form, scopes: e.target.checked ? [...form.scopes, scope] : form.scopes.filter((s) => s !== scope) })}
                    />
                    <span>{text}<span className="muted block font-mono text-xs">{scope}</span></span>
                  </label>
                ))}
              </div>
            </div>
            {error && <Alert>{error}</Alert>}
            <Button type="submit" disabled={form.scopes.length === 0}>Create key</Button>
          </form>
        )}
      </Modal>

      <Modal open={Boolean(created)} onClose={() => setCreated(null)} title="Copy your API key now">
        {created && (
          <div className="space-y-3">
            <Alert tone="amber">This is the only time the key is shown. Store it in your automation tool, not in a document or chat.</Alert>
            <CopyField label="API key" value={created.key} />
            <Button onClick={() => setCreated(null)}>I have copied it</Button>
          </div>
        )}
      </Modal>
    </Section>
  )
}

export default function AdminAutomation() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('agents')

  const reload = useCallback(() => api.adminAutomation().then(setData).catch((err) => setError(err.message)), [])
  useEffect(() => {
    reload()
  }, [reload])

  return (
    <AdminLayout title="Automation">
      {error && <Alert className="mb-4">{error}</Alert>}
      {!data && !error && <p className="muted text-sm">Loading…</p>}
      {data && (
        <>
          <Tabs
            value={tab}
            onChange={setTab}
            tabs={[
              { id: 'agents', label: 'Agents' }, { id: 'posts', label: 'Posts' },
              { id: 'webhooks', label: 'Webhooks' }, { id: 'keys', label: 'API keys' },
            ]}
          />
          {tab === 'agents' && <Agents data={data} reload={reload} />}
          {tab === 'posts' && <Posts />}
          {tab === 'webhooks' && <Webhooks data={data} reload={reload} />}
          {tab === 'keys' && <ApiKeys data={data} reload={reload} />}
        </>
      )}
    </AdminLayout>
  )
}

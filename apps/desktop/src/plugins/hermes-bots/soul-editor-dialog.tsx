/**
 * Double-click editor for a bot's SOUL.md. The Details pane shows a read-only
 * preview; this dialog is the write surface. Saves go through
 * `profiles.configure` (the write twin of the preview's `profiles.describe`)
 * so a remote bot writes on its own gateway, not the foreground one.
 */

import * as sdk from '@hermes/plugin-sdk'
import {
  Button,
  ConfirmDialog,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  host,
  SegmentedControl,
  Textarea,
  useI18n,
  useQueryClient
} from '@hermes/plugin-sdk'
import { useCallback, useEffect, useState } from 'react'

import { botSelectionKey } from './data'
import { useBots } from './i18n'
import { requestForBot } from './routing'
import { ID } from './shared'
import type { RosterRow } from './types'

const MessageTextContent = typeof sdk === 'undefined' ? undefined : sdk.MessageTextContent

export function botSoulQueryKey(bot: RosterRow) {
  return [ID, 'soul', botSelectionKey(bot)] as const
}

interface SoulEditorDialogProps {
  bot: RosterRow
  initialContent: string
  onClose: () => void
  open: boolean
}

interface ConfigureSoulResult {
  applied?: { soul?: boolean }
}

export function SoulEditorDialog({ bot, initialContent, onClose, open }: SoulEditorDialogProps) {
  const { t } = useI18n()
  const b = useBots()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState(initialContent)
  const [preview, setPreview] = useState(false)
  const [busy, setBusy] = useState(false)
  const [confirmDiscard, setConfirmDiscard] = useState(false)

  useEffect(() => {
    if (!open) {
      return
    }

    setDraft(initialContent)
    setPreview(false)
    setBusy(false)
    setConfirmDiscard(false)
  }, [initialContent, open])

  const dirty = draft !== initialContent

  const save = useCallback(async () => {
    if (busy) {
      return
    }

    setBusy(true)

    try {
      const result = (await requestForBot(bot, 'profiles.configure', {
        name: bot.name,
        soul: draft
      })) as ConfigureSoulResult

      if (result?.applied?.soul === false) {
        host.notify({
          kind: 'error',
          message: b.soulEditor.saveFailed
        })
        return
      }

      await queryClient.invalidateQueries({
        queryKey: botSoulQueryKey(bot)
      })
      onClose()
    } catch (err) {
      host.notifyError(err, b.soulEditor.saveFailed)
    } finally {
      setBusy(false)
    }
  }, [b.soulEditor.saveFailed, bot, busy, draft, onClose, queryClient])

  const requestClose = useCallback(() => {
    if (busy) {
      return
    }

    if (dirty) {
      setConfirmDiscard(true)
      return
    }

    onClose()
  }, [busy, dirty, onClose])

  useEffect(() => {
    if (!open) {
      return
    }

    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        event.stopPropagation()
        void save()
      }
    }

    window.addEventListener('keydown', onKey, true)

    return () => window.removeEventListener('keydown', onKey, true)
  }, [open, save])

  return (
    <>
      <Dialog onOpenChange={value => !value && requestClose()} open={open}>
        <DialogContent
          className="flex max-w-3xl flex-col"
          data-slot="soul-editor"
          style={{
            resize: 'both',
            overflow: 'auto',
            minWidth: 420,
            minHeight: 360,
            maxWidth: '95vw',
            maxHeight: '90vh'
          }}
        >
          <DialogHeader>
            <DialogTitle>{b.soulEditor.title}</DialogTitle>
            <DialogDescription>{b.soulEditor.description(bot.name)}</DialogDescription>
          </DialogHeader>
          <div className="flex min-h-0 flex-1 flex-col gap-2">
            <SegmentedControl
              onChange={id => setPreview(id === 'preview')}
              options={[
                { id: 'edit', label: b.soulEditor.edit },
                { id: 'preview', label: b.soulEditor.preview }
              ]}
              value={preview ? 'preview' : 'edit'}
            />
            {preview ? (
              <div className="min-h-[20rem] flex-1 overflow-auto rounded-md border border-(--ui-stroke-secondary) bg-(--ui-bg-tertiary)/40 px-3 py-2">
                {MessageTextContent ? (
                  <MessageTextContent media={false} text={draft} />
                ) : (
                  <pre className="whitespace-pre-wrap font-mono text-[0.8125rem] leading-5 text-(--ui-text-secondary)">
                    {draft}
                  </pre>
                )}
              </div>
            ) : (
              <Textarea
                aria-label="SOUL.md"
                className="min-h-[20rem] flex-1 resize-none font-mono text-[0.8125rem] leading-5"
                onChange={event => setDraft(event.target.value)}
                spellCheck={false}
                value={draft}
              />
            )}
          </div>
          <DialogFooter>
            <Button disabled={busy} onClick={requestClose} type="button" variant="ghost">
              {t.common.cancel}
            </Button>
            <Button disabled={busy} onClick={() => void save()}>
              {busy ? t.common.saving : t.common.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        confirmLabel={b.soulEditor.discard}
        description={b.soulEditor.discardDescription}
        destructive
        onClose={() => setConfirmDiscard(false)}
        onConfirm={() => {
          setConfirmDiscard(false)
          onClose()
        }}
        open={confirmDiscard}
        title={b.soulEditor.discardTitle}
      />
    </>
  )
}

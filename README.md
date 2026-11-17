# reddit-reply-client

A minimal client for posting a reply to one Reddit thread, from one person's own account.

It exists so the behaviour is easy to audit: the whole program is one file, it authenticates with the password grant of a script app (so it can only act as the single account that owns the credentials), it reads nothing except the thread it replies to, and it can post one comment and delete it again. It never votes, never sends messages, never touches moderation endpoints.

## Use

```bash
export REDDIT_CLIENT_ID=...      # script app
export REDDIT_CLIENT_SECRET=...
export REDDIT_USERNAME=...
export REDDIT_PASSWORD=...

python3 reddit_client.py whoami
python3 reddit_client.py reply --url https://www.reddit.com/r/devops/comments/abc123/title/ --file reply.md --dry-run
python3 reddit_client.py reply --url ... --file reply.md
python3 reddit_client.py delete --id t1_xyz
```

`--dry-run` prints the target thing id and the character count without writing anything.

## Behaviour boundaries

- One account: the credentials owner. There is no multi-account mode.
- One comment per invocation. No queue, no scheduling inside the client.
- Read scope: the thread being answered, reached through the URL the caller provides.
- No votes, no flair, no moderator actions, no private messages, no subreddit creation.

Run by [Indra Prasetya](https://blog.qansa.web.id).

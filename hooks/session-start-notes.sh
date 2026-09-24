# SessionStart hook: prints only Next Steps and Blockers / Open Questions from the last two session notes.
# The other sections describe work already done, which with parallel sessions is usually another session's.
filter() { awk '/^### (Next Steps|Blockers \/ Open Questions)/{p=1; print; next} /^##/{p=0} p'; }
if [ -d session-notes ] && ls session-notes/*.md >/dev/null 2>&1; then
  echo '--- LAST SESSION CONTEXT (Next Steps + Blockers only) ---'
  ls -1 session-notes/*.md | sort | tail -n 2 | while IFS= read -r f; do
    echo "## $(basename "$f")"
    filter < "$f"
    echo
  done
  echo '--- END LAST SESSION ---'
elif [ -f SESSION_NOTES.md ]; then
  echo '--- LAST SESSION CONTEXT (Next Steps + Blockers only) ---'
  awk '/^## Session/{blocks[++n]=""} {blocks[n]=blocks[n]$0"\n"} END{start=n-1; if(start<1) start=1; for(i=start;i<=n;i++) printf "%s",blocks[i]}' SESSION_NOTES.md | filter
  echo '--- END LAST SESSION ---'
fi

#!/bin/bash
# push 后 token 零残留检查 (凭据卫生铁律)
cd /home/agentuser/AgentFramework
echo "git config ghp count: $(git config --list 2>/dev/null | grep -c ghp_)"
echo "remote url: $(git remote get-url origin)"
if [ -f ~/.git-credentials ]; then echo "credentials file: EXISTS"; else echo "credentials file: NONE"; fi
echo "config residue: $(grep -c 'ghp_' .git/config)"
if [ -f .git/FETCH_HEAD ]; then echo "FETCH_HEAD residue: $(grep -c 'ghp_' .git/FETCH_HEAD)"; fi
if [ -f .git/packed-refs ]; then echo "packed-refs residue: $(grep -c 'ghp_' .git/packed-refs)"; fi
echo "repo tracked files residue scan:"
git ls-files | xargs grep -lE 'ghp_[A-Za-z0-9]{20}' 2>/dev/null | head -5 || echo "  CLEAN"

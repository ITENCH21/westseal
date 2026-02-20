import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, '/Users/ivan/евро сеал')
import django; django.setup()

from apps.support.models import SupportChatMessage, SupportChatThread
for t in SupportChatThread.objects.all():
    msgs = t.messages.order_by('created_at')
    if msgs.exists():
        print(f"\n=== Thread {t.id} user={t.user} ===")
        for m in msgs:
            print(f"  id={m.id} author={m.author} is_bot={m.is_bot} via={m.via!r} body={m.body[:25]!r}")

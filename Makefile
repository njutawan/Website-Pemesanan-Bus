# Perintah pengembangan Nusantara Trans.
# DEBUG default MATI (fail-closed); target dev menyalakannya eksplisit.
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
MANAGE = $(PY) manage.py

.PHONY: dev migrate seed check test audit review secrets deploy-check backup-verify

dev:            ## Jalankan server pengembangan (DEBUG=1)
	DJANGO_DEBUG=1 $(MANAGE) runserver

migrate:        ## Terapkan migrasi
	DJANGO_DEBUG=1 $(MANAGE) migrate

seed:           ## Isi data demo (admin acak bila DJANGO_ADMIN_PASSWORD kosong)
	DJANGO_DEBUG=1 $(MANAGE) seed_data

check:          ## System check mode pengembangan
	DJANGO_DEBUG=1 $(MANAGE) check

test:           ## Seluruh test suite
	DJANGO_DEBUG=1 $(MANAGE) test

audit:          ## 20 kontrol keamanan aplikasi
	$(MANAGE) security_audit

review:         ## 19 kontrol hardening (secret/env/DB/upload)
	$(MANAGE) security_review

secrets:        ## Pindai rahasia di repo + riwayat git
	./deploy/scan_secrets.sh

deploy-check:   ## Gate produksi: butuh env produksi lengkap
	$(MANAGE) check --deploy --fail-level WARNING
	$(MANAGE) security_audit
	$(MANAGE) security_review

backup-verify:  ## Drill restore backup terakhir (butuh env PG*)
	./deploy/verify_backup.sh

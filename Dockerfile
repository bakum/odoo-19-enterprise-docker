FROM odoo:19

# Install extra dependencies for custom modules.
USER root
COPY requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then \
      pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt; \
    fi
USER odoo

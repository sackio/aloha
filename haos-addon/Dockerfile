ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python dependencies
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy the Aloha Python package
COPY aloha/ /app/aloha/

# Copy built React frontend static files
COPY frontend/dist/ /app/aloha/frontend/dist/

# Copy the add-on run script
COPY haos-addon/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]

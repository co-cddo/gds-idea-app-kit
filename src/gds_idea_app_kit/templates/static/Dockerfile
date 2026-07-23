FROM node:22-slim AS base
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

FROM base AS development
EXPOSE 8080
CMD ["npx", "@11ty/eleventy", "--serve", "--port=8080"]

FROM public.ecr.aws/lambda/python:3.12 AS build
RUN dnf install -y tar xz \
    && curl -fsSL https://nodejs.org/dist/v22.16.0/node-v22.16.0-linux-x64.tar.xz -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz
ENV ELEVENTY_OUTPUT_DIR=/tmp/_site
COPY --from=base /app /var/task/site
COPY handler.py /var/task/
WORKDIR /var/task/site
CMD ["handler.handler"]

FROM node:20-slim AS base
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

FROM base AS development
EXPOSE 8080
CMD ["npx", "@11ty/eleventy", "--serve", "--port=8080"]

FROM public.ecr.aws/lambda/python:3.12 AS build
RUN dnf install -y nodejs20 npm
COPY --from=base /app /var/task/site
COPY handler.py /var/task/
WORKDIR /var/task/site
CMD ["handler.handler"]

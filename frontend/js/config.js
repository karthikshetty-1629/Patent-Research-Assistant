// Runtime configuration for the static frontend.
// Replace API_BASE_URL with your deployed API Gateway invoke URL
// (see infra/template.yaml outputs after `sam deploy`).
window.APP_CONFIG = {
  API_BASE_URL: "https://REPLACE_ME.execute-api.us-east-1.amazonaws.com",
};

const { Anthropic } = require("@anthropic-ai/sdk");

console.log("API_KEY:", process.env.ANTHROPIC_API_KEY ? "SET" : "NOT SET");
console.log("BASE_URL:", process.env.ANTHROPIC_BASE_URL || "(default)");

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,   
  baseURL: process.env.ANTHROPIC_BASE_URL || "https://api.anthropic.com",
});

console.log("Client created successfully");
console.log("API Key used:", client.apiKey === process.env.ANTHROPIC_API_KEY ? "YES" : "NO");

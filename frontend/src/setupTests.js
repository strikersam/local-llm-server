import '@testing-library/jest-dom';

// react-router-dom v7 uses TextEncoder/TextDecoder which jsdom doesn't provide
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

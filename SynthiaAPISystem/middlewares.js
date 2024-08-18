const { isServerReady } = require('./utils');

// Middleware to handle server initialization
function checkServerReady(req, res, next) {
  if (!isServerReady()) {
    res.status(503).json({ success: false, message: 'Server is warming up, please try again later.' });
  } else {
    next();
  }
}

module.exports = { checkServerReady };

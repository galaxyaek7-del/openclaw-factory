import core from './core.js';

export default {
  fetch(request, env) {
    return core.handleLeadRequest(request, env);
  },
};

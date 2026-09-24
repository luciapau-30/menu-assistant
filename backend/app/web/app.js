const $ = id => document.getElementById(id);
let token = '', analysisId = null;
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
async function api(path, method = 'GET', data) {
  const headers = token ? {Authorization: `Bearer ${token}`} : {};
  if (data && !(data instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api/v1${path}`, {method, headers, body: data ? (data instanceof FormData ? data : JSON.stringify(data)) : undefined});
  const result = await response.json();
  if (!response.ok) {
    const detail = result.detail;
    throw new Error(Array.isArray(detail) ? detail.map(x => x.msg).join('; ') : detail || 'Request failed. Please retry.');
  }
  return result;
}
async function busy(action, text) {
  const buttons = [...document.querySelectorAll('button')];
  buttons.forEach(b => b.disabled = true); message(text);
  try { await action(); } catch (error) { message(error.message, true); }
  finally { buttons.forEach(b => b.disabled = false); }
}
$('auth-form').addEventListener('submit', event => {
  event.preventDefault(); const register = event.submitter.value === 'register';
  busy(async () => {
    const credentials = {email: $('email').value, password: $('password').value};
    if (register) {
      if (!$('name').value.trim()) throw new Error('Enter your name to create an account.');
      await api('/auth/register', 'POST', {...credentials, name: $('name').value.trim()});
    }
    token = (await api('/auth/login', 'POST', credentials)).access_token;
    const [options, profile] = await Promise.all([api('/profile/options'), api('/profile')]);
    $('profile-options').replaceChildren();
    for (const [key, values] of Object.entries(options)) {
      const label = node('label', key.replaceAll('_', ' '));
      const select = node('select'); select.multiple = true; select.name = key;
      for (const value of values) { const option = node('option', value); option.value = value; option.selected = profile[key].includes(value); select.append(option); }
      label.append(select); $('profile-options').append(label);
    }
    $('password').value = ''; $('account').hidden = true; $('workspace').hidden = false; $('logout').hidden = false;
    message(`Welcome, ${profile.name}. Start by saving your dietary profile.`);
  }, 'Opening your account…');
});
$('logout').onclick = () => location.reload();
$('profile-form').onsubmit = event => {
  event.preventDefault(); busy(async () => {
    const profile = {};
    for (const select of $('profile-options').querySelectorAll('select')) profile[select.name] = [...select.selectedOptions].map(x => x.value);
    await api('/profile', 'PUT', profile); message('Profile saved. You can upload a menu now.');
  }, 'Saving your profile…');
};
function addItem(item = {name: '', ingredients: []}) {
  const row = node('div', undefined, 'item');
  const nameLabel = node('label', 'Item name'); const name = node('input'); name.value = item.name; name.required = true; name.maxLength = 300; name.className = 'item-name'; nameLabel.append(name);
  const label = node('label', 'Ingredients — one per line'); const input = node('textarea'); input.rows = 4; input.value = item.ingredients.join('\n'); input.required = true; input.className = 'item-ingredients'; label.append(input);
  row.append(nameLabel, label);
  if (item.source_text) row.append(node('p', `Read from image: ${item.source_text}`, 'hint'));
  const remove = node('button', 'Remove item', 'secondary'); remove.type = 'button'; remove.onclick = () => row.remove(); row.append(remove); $('items').append(row);
}
function showAnalysis(data) {
  analysisId = data.analysis_id; $('saved-id').value = analysisId;
  $('analysis-number').textContent = `Analysis ${analysisId}. Keep this number to reopen your saved results.`;
  $('items').replaceChildren(); $('reports').replaceChildren(); $('extraction-warnings').replaceChildren();
  $('review').hidden = data.status === 'COMPLETED' || data.status === 'PROCESSING'; $('results').hidden = data.status !== 'COMPLETED';
  for (const warning of data.extraction?.warnings || []) $('extraction-warnings').append(node('p', warning, 'warning'));
  for (const item of data.extraction?.items || [{name: '', ingredients: []}]) addItem(item);
  for (const report of data.reports || []) {
    const card = node('article', undefined, 'card');
    card.append(node('h3', report.menu_item_name), node('p', report.compatibility_score === null ? 'Not fully assessed' : `${report.compatibility_score} / 100`, 'score'));
    card.append(node('p', `Ingredient lookup confidence: ${report.confidence}`), node('p', report.ingredients.join(', '), 'hint'));
    if (report.safety_score === 0) card.append(node('p', 'Potential dietary conflict. Verify with the restaurant.', 'warning'));
    if (report.safety_score === null) card.append(node('p', 'Dietary checks are incomplete.', 'warning'));
    for (const [goal, score] of Object.entries(report.goal_scores)) card.append(node('p', `${goal}: ${score}/100${report.unassessed_goals.includes(goal) ? ' (partial data)' : ''}`));
    if (report.unassessed_goals.length) card.append(node('p', `Not fully assessed: ${report.unassessed_goals.join(', ')}`, 'warning'));
    for (const warning of report.warnings) card.append(node('p', warning, 'warning'));
    for (const [title, values] of [['Potential conflicts', [...report.detected_allergens, ...report.detected_restrictions]], ['Possible changes', report.suggested_modifications], ['Ask the restaurant', report.questions_to_ask]]) {
      if (values.length) { card.append(node('h3', title)); const list = node('ul'); for (const value of values) list.append(node('li', value)); card.append(list); }
    }
    $('reports').append(card);
  }
  if (data.error_message) message(data.error_message, true);
  else if (data.status === 'COMPLETED') message(`Reports saved under analysis ${analysisId}.`);
  else if (data.status === 'PROCESSING') message('This analysis is still processing. Open it again shortly.');
  else message('Review the extracted items, or enter ingredients manually, then generate your reports.');
}
$('upload-form').onsubmit = event => {
  event.preventDefault(); busy(async () => {
    const file = $('image').files[0]; if (file.size > 4 * 1024 * 1024) throw new Error('Choose an image smaller than 4 MiB.');
    const form = new FormData(); form.append('image', file); form.append('type', $('image-type').value);
    const upload = await api('/analysis/upload', 'POST', form); showAnalysis(upload);
    message('Reading your image…'); showAnalysis(await api(`/analysis/${analysisId}/extract`, 'POST'));
  }, 'Uploading your image…');
};
$('retry').onclick = () => busy(async () => showAnalysis(await api(`/analysis/${analysisId}/extract`, 'POST')), 'Reading your image…');
$('add-item').onclick = () => addItem();
$('load-form').onsubmit = event => { event.preventDefault(); busy(async () => showAnalysis(await api(`/analysis/${$('saved-id').value}`)), 'Opening saved analysis…'); };
$('report-form').onsubmit = event => {
  event.preventDefault(); busy(async () => {
    const items = [...$('items').children].map(row => ({name: row.querySelector('.item-name').value.trim(), ingredients: row.querySelector('.item-ingredients').value.split('\n').map(x => x.trim()).filter(Boolean)}));
    if (!items.length || items.some(x => !x.ingredients.length)) throw new Error('Add at least one item and its ingredients.');
    const result = await api(`/analysis/${analysisId}/report`, 'POST', {items});
    if (result.status === 'FAILED') message(result.error_message, true);
    else showAnalysis(result);
  }, 'Checking your reviewed ingredients…');
};

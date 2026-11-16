(() => {
  const root = document.querySelector('#full-command-catalog');
  if (!root) return;
  const search = document.querySelector('#command-search');
  const scope = document.querySelector('#command-scope');
  const count = document.querySelector('#command-count');
  let catalog = null;
  const esc = (value) => String(value).replace(/[&<>\"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[ch]));
  const render = () => {
    if (!catalog) return;
    const query = (search.value || '').trim().toLowerCase();
    const selected = scope.value;
    let shown = 0;
    const html = catalog.groups.map(group => {
      if (selected !== 'all' && group.scope !== selected) return '';
      const commands = group.commands.filter(item => {
        const hay = `${group.scope} ${group.section} ${item.command} ${item.description}`.toLowerCase();
        return !query || hay.includes(query);
      });
      if (!commands.length) return '';
      shown += commands.length;
      return `<details class="catalog-group" open><summary><span>${esc(group.section)}</span><small>${esc(group.scope)} · ${commands.length}</small></summary><div class="catalog-rows">${commands.map(item => `<div class="catalog-row"><code>${esc(item.command)}</code><span>${esc(item.description)}</span></div>`).join('')}</div></details>`;
    }).join('');
    root.innerHTML = html || '<div class="docs-note">No commands match that search.</div>';
    count.textContent = `${shown} of ${catalog.command_count} commands`;
  };
  fetch('assets/command-catalog.json').then(response => response.json()).then(data => {
    catalog = data;
    [...new Set(data.groups.map(group => group.scope))].forEach(value => {
      const option = document.createElement('option'); option.value = value; option.textContent = value; scope.appendChild(option);
    });
    render();
  }).catch(() => { root.innerHTML = '<div class="docs-note">The command catalog could not be loaded.</div>'; });
  search.addEventListener('input', render);
  scope.addEventListener('change', render);
})();

"""Functional browser scenarios shared with the local smoke runner (CDP)."""
import json
import math


def select(evaluate, selector, value):
    evaluate("(() => { const input = document.querySelector(" + json.dumps(selector) + "); input.value = " + json.dumps(value) + "; input.dispatchEvent(new Event('change', { bubbles: true })); })()")


def explorer(evaluate, call, wait, click, screenshot, get, post, api, text_contains):
    post(api + '/api/simulator/start', {})
    wait(text_contains('DATOS SIMULADOS'))
    select(evaluate, 'select[aria-label="Banda de telemetría"]', 'low_beta')
    select(evaluate, 'select[aria-label="Sensor de telemetría"]', 'F3')
    select(evaluate, 'select[aria-label="Ventana temporal"]', '15')
    wait("document.querySelector('.live-chart svg[aria-label]')?.getAttribute('aria-label').includes('F3')")
    evaluate("[...document.querySelectorAll('.interactive-legend button')].find(item=>item.textContent.includes('Gamma')).click()")
    wait("document.querySelectorAll('.live-chart svg > path').length === 2")
    screenshot('telemetry-filters.png')
    click('Explorador cerebral')
    wait(text_contains('Otra perspectiva de tu señal.'))
    wait("document.querySelector('.sensor-inspector [data-band=alpha]') && /[0-9]/.test(document.querySelector('.sensor-inspector [data-band=alpha]').textContent)")
    select(evaluate, 'select[aria-label="Sensor del explorador"]', 'O1')
    wait("document.querySelector('[data-testid=selected-sensor]').textContent === 'O1'")
    assert evaluate("document.querySelector('select[aria-label=\"Banda del explorador\"]').value") == 'alpha'
    assert evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot('mobile-sensors.png')
    select(evaluate, 'select[aria-label="Sensor del explorador"]', 'AF3')
    post(api + '/api/simulator/config', {'scenario':'POOR_QUALITY','poor_sensors':['AF3']}, method='PUT')
    wait("document.querySelector('.inspector-quality dd') && Number(document.querySelector('.inspector-quality dd').textContent.split('/')[0]) < 3")
    post(api + '/api/simulator/disconnect', {'duration_s': None})
    wait("document.querySelector('.sensor-inspector [data-band=alpha]').textContent === '—'")
    post(api + '/api/simulator/reconnect', {})
    post(api + '/api/simulator/config', {'scenario':'ACTIVITY_DEMO'}, method='PUT')
    wait("/[0-9]/.test(document.querySelector('.sensor-inspector [data-band=alpha]').textContent)")
    select(evaluate, 'select[aria-label="Sensor del explorador"]', 'O1')
    call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
    click('Vista 3D')
    wait("document.querySelector('.brain-canvas canvas') !== null", 30)
    evaluate("document.querySelector('.brain-canvas').scrollIntoView({block:'center'})")
    assert evaluate("document.querySelector('[data-testid=selected-sensor]').textContent") == 'O1'
    # Project a real electrode using the documented initial camera, then click it.
    rect = evaluate("JSON.parse(JSON.stringify(document.querySelector('.brain-canvas canvas').getBoundingClientRect()))")
    def dot(a,b): return sum(x*y for x,y in zip(a,b))
    def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    def normalized(a):
        length = math.sqrt(dot(a,a))
        return [value/length for value in a]
    camera = [2.5,2.2,3.1]
    forward = normalized([-v for v in camera]); right = normalized(cross(forward,[0,1,0])); up = cross(right,forward)
    position = [.27, math.sqrt(1-.27**2-.74**2)*.95, .74*1.15]  # AF4
    relative = [a-b for a,b in zip(position,camera)]
    depth = dot(relative,forward); tangent = math.tan(math.radians(42)/2)
    nx = dot(relative,right)/(depth*tangent*(rect['width']/rect['height'])); ny = dot(relative,up)/(depth*tangent)
    x = rect['left']+(nx+1)*rect['width']/2; y=rect['top']+(1-ny)*rect['height']/2
    for kind in ['mousePressed','mouseReleased']:
        call('Input.dispatchMouseEvent', {'type':kind,'x':x,'y':y,'button':'left','clickCount':1})
    wait("document.querySelector('[data-testid=selected-sensor]').textContent === 'AF4'")
    screenshot('brain-3d.png')
    click('Restablecer orientación')
    evaluate("document.querySelector('.brain-canvas canvas').focus()")
    call('Input.dispatchKeyEvent', {'type':'keyDown','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
    call('Input.dispatchKeyEvent', {'type':'keyUp','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
    evaluate("document.querySelector('[aria-label=\"Acercar modelo\"]').click()")
    evaluate("document.querySelector('[aria-label=\"Alejar modelo\"]').click()")
    evaluate("[...document.querySelectorAll('.explorer-filters input[type=checkbox]')][0].click()")
    assert not evaluate("document.querySelector('.explorer-filters input[type=checkbox]').checked")
    evaluate("document.querySelector('.explorer-filters input[type=checkbox]').click()")
    click('Vista 2D')
    assert evaluate("document.querySelector('[data-testid=selected-sensor]').textContent") == 'AF4'
    evaluate("document.querySelector('.theme-toggle').click()")
    screenshot('explorer-dark.png')
    evaluate("document.querySelector('.theme-toggle').click()")
    click('Mi sesión')
    click('Nueva sesión')
    wait("document.querySelector('dialog').open")
    select(evaluate, 'dialog select', 'REAL_EMOTIV')
    wait("document.querySelector('select[aria-label=\"Modelo de EMOTIV\"]') !== null")
    assert evaluate("document.querySelector('select[aria-label=\"Modelo de EMOTIV\"]').value") == ''
    select(evaluate, 'select[aria-label="Modelo de EMOTIV"]', 'INSIGHT')
    evaluate("document.querySelector('.device-preparation input[type=checkbox]').click()")
    click('Siguiente paso')
    wait(text_contains('Insight no usa los fieltros'))
    click('Anterior')
    select(evaluate, 'select[aria-label="Modelo de EMOTIV"]', 'EPOCX')
    evaluate("document.querySelector('.device-preparation input[type=checkbox]').click()")
    click('Siguiente paso')
    wait(text_contains('Hidrata los fieltros'))
    assert evaluate("document.querySelector('dialog form > .actions button').disabled"), 'Real source must require preparation'
    screenshot('device-preparation.png')
    click('Cancelar')
    call('Emulation.setDeviceMetricsOverride', {'width':375,'height':900,'deviceScaleFactor':1,'mobile':True})
    return ['live-band-sensor-window-legend-filters', 'sensor-selection-2d', 'quality-loss-reconnect-without-fabricated-data', 'webgl-3d-raycast-controls', 'shared-inspector-2d-3d', 'dark-theme', 'model-specific-preparation']


def navigation(evaluate, click, wait, get, api, sid):
    before = get(api + '/api/sessions/' + str(sid))['session']
    click('Explorador cerebral'); click('Mi sesión')
    after = get(api + '/api/sessions/' + str(sid))['session']
    assert [(p['id'],p['started_at']) for p in before['phases']] == [(p['id'],p['started_at']) for p in after['phases']]
    return ['navigation-preserves-phase']


def pause_navigation(evaluate, click, wait, text_contains):
    before = evaluate("document.querySelector('.experience-task .timer').textContent")
    select(evaluate, '.experience-task select', '2')
    click('Explorador cerebral'); click('Mi sesión')
    wait(text_contains('el registro EEG de esta fase continúa'))
    assert evaluate("document.querySelector('.experience-task .timer').textContent") == before
    assert evaluate("document.querySelector('.experience-task select').value") == '2'
    return ['navigation-preserves-guide-pause']


def coding(evaluate, call, wait, click, screenshot, get, api, text_contains):
    call('Network.enable')
    call('Network.setBlockedURLs', {'urls': [api + '/api/coding/tasks']})
    click('Mi sesión'); click('Nueva sesión')
    wait("document.querySelector('dialog').open")
    select(evaluate, 'dialog select', 'SIMULATED')
    # Find the activity select by its option, without depending on layout order.
    evaluate("(() => { const select=[...document.querySelectorAll('dialog select')].find(item=>[...item.options].some(option=>option.value==='CODING')); select.value='CODING'; select.dispatchEvent(new Event('change',{bubbles:true})); })()")
    evaluate("document.querySelector('dialog details').open=true")
    evaluate("document.querySelectorAll('dialog input[type=checkbox]')[1].click()")
    click('Comenzar sesión'); wait(text_contains('Comienza con una pausa.'))
    sid = get(api + '/api/sessions/active')['id']
    assert get(api + '/api/sessions/active')['activity_kind'] == 'CODING'
    wait(text_contains('Explora un fragmento de código.'), 16)
    wait(text_contains('Reintentar catálogo de tareas'))
    call('Network.setBlockedURLs', {'urls': []})
    click('Reintentar catálogo de tareas')
    wait("document.querySelector('.experience-task select option') !== null")
    click('Comenzar lectura de código'); wait(text_contains('Comprender un recorrido'))
    evaluate("document.querySelectorAll('input[name=coding-choice]')[1].click()")
    click('Enviar respuesta'); wait(text_contains('Respuesta correcta. Puedes continuar'))
    assert len(get(api + '/api/sessions/' + str(sid))['coding_answers']) == 1
    screenshot('neurocode.png')
    click('Terminar tarea'); wait(text_contains('¿Cuánta tensión percibes ahora?'))
    evaluate("document.querySelectorAll('.experience-task .rating button')[4].click()")
    evaluate("document.querySelector('.subjective-extras').open=true")
    evaluate("[...document.querySelectorAll('.subjective-extras label')].find(item=>item.textContent.includes('Esfuerzo')).querySelector('input').focus()")
    call('Input.insertText', {'text':'7'})
    click('Guardar y continuar'); wait(text_contains('Ahora, baja el ritmo.'))
    click('Comenzar pausa'); wait(text_contains('Pausar guía')); click('Terminar y continuar')
    wait(text_contains('Antes de ver tus resultados'))
    evaluate("document.querySelectorAll('.experience-task .rating button')[2].click()")
    click('Guardar y continuar'); wait(text_contains('Tareas de código resueltas'))
    summary = get(api + '/api/sessions/' + str(sid) + '/summary')
    assert summary['coding']['n_completed'] == 1 and summary['math'] is None
    assert any(report['moment']=='POST_CODING' and report['effort']==7 for report in summary['self_reports'])
    screenshot('neurocode-results.png')
    click('Cerrar resultados y descartar')
    return ['neurocode-guided-flow-and-effort']


def fallback(evaluate, call, wait, click, screenshot, text_contains):
    call('Page.addScriptToEvaluateOnNewDocument', {'source': "const original=HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext=function(kind,...args){if(['webgl','webgl2','experimental-webgl'].includes(kind))return null; return original.call(this,kind,...args);};"})
    previous_origin = evaluate('performance.timeOrigin')
    call('Page.reload')
    wait('performance.timeOrigin !== ' + str(previous_origin))
    wait(text_contains('Un paso a la vez.'))
    click('Explorador cerebral'); click('Vista 3D')
    wait(text_contains('WebGL no está disponible'))
    assert evaluate("document.querySelector('.head-map') !== null && document.querySelector('.brain-canvas canvas') === null")
    call('Emulation.setDeviceMetricsOverride', {'width':375,'height':900,'deviceScaleFactor':1,'mobile':True})
    assert evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot('webgl-fallback-mobile.png')
    return ['webgl-unavailable-fallback-2d']

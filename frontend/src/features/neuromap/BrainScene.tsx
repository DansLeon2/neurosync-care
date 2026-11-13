import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { SensorReading } from './sensorModel';
import { cranialPosition } from './sensorModel';

interface Props {
  readings: SensorReading[]; selected: string; showSensors: boolean;
  onSelect: (id: string) => void; onUnavailable: (reason: string) => void;
}
type Controller = { update: () => void; reset: () => void; zoom: (factor: number) => void };

/** Own procedural illustration. Electrode colors come from the same model as 2D. */
export default function BrainScene(props: Props) {
  const host = useRef<HTMLDivElement>(null);
  const current = useRef(props);
  current.current = props;
  const controller = useRef<Controller | null>(null);

  useEffect(() => {
    const container = host.current;
    if (!container) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }); }
    catch { current.current.onUnavailable('WebGL no está disponible en este equipo. La vista 2D conserva todos los datos.'); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setClearColor(0x000000, 0);
    const canvas = renderer.domElement;
    canvas.tabIndex = 0;
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', 'Cabeza ilustrativa 3D con sensores seleccionables. Arrastra para girar o usa las flechas.');
    container.appendChild(canvas);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, .1, 30);
    camera.position.set(2.5, 2.2, 3.1);
    const controls = new OrbitControls(camera, canvas);
    controls.enablePan = false; controls.minDistance = 2.5; controls.maxDistance = 7;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x756488, 2.5));
    const light = new THREE.DirectionalLight(0xffffff, 2.5); light.position.set(3, 4, 3); scene.add(light);

    const skull = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 24), new THREE.MeshPhongMaterial({ color: 0xb9a8d7, transparent: true, opacity: .11, wireframe: true, depthWrite: false }));
    skull.scale.set(1, .95, 1.15); scene.add(skull);
    // Folded ellipsoids are visual motifs, not anatomical or measured surfaces.
    for (const side of [-1, 1]) {
      const geometry = new THREE.SphereGeometry(1, 48, 32);
      const positions = geometry.attributes.position;
      for (let i = 0; i < positions.count; i++) {
        const x = positions.getX(i), y = positions.getY(i), z = positions.getZ(i);
        const fold = 1 + .045 * Math.sin(y * 28 + z * 12) * Math.cos(z * 18 + x * 10);
        positions.setXYZ(i, x * .39 * fold, y * .59 * fold, z * .78 * fold);
      }
      geometry.computeVertexNormals();
      const mesh = new THREE.Mesh(geometry, new THREE.MeshPhongMaterial({ color: 0xc0add7, shininess: 12 }));
      mesh.position.set(side * .35, -.03, -.03); scene.add(mesh);
    }
    const nose = new THREE.Mesh(new THREE.ConeGeometry(.1, .25, 3), new THREE.MeshPhongMaterial({ color: 0x9f8dba, transparent: true, opacity: .6 }));
    nose.rotation.x = Math.PI / 2; nose.position.set(0, -.12, 1.2); scene.add(nose);
    const nodes = new Map<string, THREE.Mesh<THREE.SphereGeometry, THREE.MeshPhongMaterial>>();
    let lastIds = '';
    const draw = () => renderer.render(scene, camera);
    const update = () => {
      const { readings, selected, showSensors } = current.current;
      const ids = readings.map(reading => reading.id).join(',');
      if (ids !== lastIds) {
        nodes.forEach(node => { scene.remove(node); node.geometry.dispose(); node.material.dispose(); }); nodes.clear();
        readings.forEach(reading => {
          const node = new THREE.Mesh(new THREE.SphereGeometry(.065, 16, 12), new THREE.MeshPhongMaterial());
          node.position.fromArray(cranialPosition(reading.x, reading.y)); node.userData.sensor = reading.id;
          scene.add(node); nodes.set(reading.id, node);
        });
        lastIds = ids;
      }
      readings.forEach(reading => {
        const node = nodes.get(reading.id)!;
        node.visible = showSensors; node.material.color.set(reading.color);
        node.material.emissive.set(reading.id === selected ? 0x62447e : 0x000000);
        node.scale.setScalar(reading.id === selected ? 1.5 : 1);
      });
      draw();
    };
    const reset = () => { camera.position.set(2.5, 2.2, 3.1); controls.target.set(0, 0, 0); controls.update(); draw(); };
    const zoom = (factor: number) => { camera.position.multiplyScalar(factor); camera.position.setLength(THREE.MathUtils.clamp(camera.position.length(), 2.5, 7)); controls.update(); draw(); };
    const observer = new ResizeObserver(() => {
      const width = Math.max(1, container.clientWidth), height = Math.max(1, container.clientHeight);
      renderer.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix(); draw();
    });
    observer.observe(container);
    const raycaster = new THREE.Raycaster();
    let pointerStart = { x: 0, y: 0 };
    const onDown = (event: PointerEvent) => { pointerStart = { x: event.clientX, y: event.clientY }; };
    const onUp = (event: PointerEvent) => {
      if (Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 5) return;
      const rect = canvas.getBoundingClientRect();
      raycaster.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), camera);
      const hit = raycaster.intersectObjects([...nodes.values()].filter(node => node.visible))[0];
      if (hit) current.current.onSelect(hit.object.userData.sensor);
    };
    const onKey = (event: KeyboardEvent) => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') zoom(event.key === 'ArrowUp' ? .9 : 1.1);
      else { camera.position.applyAxisAngle(new THREE.Vector3(0,1,0), event.key === 'ArrowLeft' ? -.15 : .15); controls.update(); draw(); }
    };
    const onLost = (event: Event) => { event.preventDefault(); current.current.onUnavailable('Se perdió el contexto gráfico. Puedes continuar en 2D.'); };
    canvas.addEventListener('pointerdown', onDown); canvas.addEventListener('pointerup', onUp);
    canvas.addEventListener('keydown', onKey); canvas.addEventListener('webglcontextlost', onLost);
    controls.addEventListener('change', draw);
    controller.current = { update, reset, zoom }; update();
    return () => {
      controller.current = null; observer.disconnect();
      canvas.removeEventListener('pointerdown', onDown); canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('keydown', onKey); canvas.removeEventListener('webglcontextlost', onLost);
      controls.removeEventListener('change', draw); controls.dispose();
      scene.traverse(object => { if (object instanceof THREE.Mesh) { object.geometry.dispose(); const materials = Array.isArray(object.material) ? object.material : [object.material]; materials.forEach(material => material.dispose()); } });
      renderer.dispose(); renderer.forceContextLoss(); canvas.remove();
    };
  }, []);
  useEffect(() => { controller.current?.update(); }, [props.readings, props.selected, props.showSensors]);
  return <div className="brain-view">
    <div className="brain-canvas" ref={host} data-testid="brain-scene" />
    <div className="brain-controls" role="group" aria-label="Controles de orientación 3D">
      <button className="button subtle compact" onClick={() => controller.current?.reset()}>Restablecer orientación</button>
      <button className="button subtle compact" aria-label="Acercar modelo" onClick={() => controller.current?.zoom(.85)}>＋</button>
      <button className="button subtle compact" aria-label="Alejar modelo" onClick={() => controller.current?.zoom(1.15)}>−</button>
    </div>
    <p className="muted">Arrastra para girar · rueda o pellizco para acercar · flechas con el modelo enfocado.</p>
  </div>;
}

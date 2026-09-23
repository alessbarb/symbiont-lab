import * as THREE from 'three';

/** Convert a PyBullet [px, py, pz] position to Three.js [x, y, z]. */
export function pbPos(px, py, pz) {
  return [px, pz, -py];
}

/** Convert a PyBullet [qx, qy, qz, qw] quaternion to a THREE.Quaternion. */
export function pbQuat(qx, qy, qz, qw) {
  return new THREE.Quaternion(qx, qz, -qy, qw);
}

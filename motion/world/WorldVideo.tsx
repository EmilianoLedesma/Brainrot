import React from 'react';
import {AbsoluteFill} from 'remotion';
import type {Script,Pack} from './kit';
import {makeZebra} from './packs/zebra';
import {makeBirds} from './packs/birds';
import {makeGeneric} from './packs/generic';

// One continuous 3D world per video. brainrot/world/script.py writes `script`; `pack` is the manifest id (brainrot/world/packs/<id>.json) of the renderer.
const PACKS:Record<string,(s:Script)=>Pack>={zebra:makeZebra,birds:makeBirds,generic:makeGeneric};
export type WorldProps={pack:string,script:Script|null};
export const defaultWorldProps:WorldProps={pack:'',script:null};

export function WorldVideo({pack,script}:WorldProps){
  const Scene=React.useMemo(()=>{
    if(!script)return null;
    const make=PACKS[pack];
    if(!make)throw new Error(`no renderer for scene pack ${pack}`);
    return make(script);
  },[pack,script]);
  return Scene?<Scene/>:<AbsoluteFill style={{background:'#D6EAF6'}}/>;
}

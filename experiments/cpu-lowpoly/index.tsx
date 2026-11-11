import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Cpu,CPU_FRAMES} from './Cpu';
registerRoot(()=><Composition id="Cpu" component={Cpu} width={1080} height={1920} fps={30} durationInFrames={CPU_FRAMES}/>);

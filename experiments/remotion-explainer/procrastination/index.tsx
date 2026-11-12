import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Procrastination,PROCRASTINATION_FRAMES} from './Procrastination';
import {ProcrastinationFull,PROCRASTINATION_FULL_FRAMES} from './ProcrastinationFull';
registerRoot(()=><>
  <Composition id="Procrastination" component={Procrastination} width={1080} height={1920} fps={30} durationInFrames={PROCRASTINATION_FRAMES}/>
  <Composition id="ProcrastinationFull" component={ProcrastinationFull} width={1080} height={1920} fps={30} durationInFrames={PROCRASTINATION_FULL_FRAMES}/>
</>);

import React from 'react';
import { Composition } from 'remotion';
import { Course, durationOf, FPS } from './Course.jsx';
import sample from '../public/course.json';

export const Root = () => (
  <Composition
    id="Course"
    component={Course}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={durationOf(sample)}
    defaultProps={sample}
    calculateMetadata={({ props }) => ({ durationInFrames: durationOf(props) })}
  />
);

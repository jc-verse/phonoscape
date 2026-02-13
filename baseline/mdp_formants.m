function data = mdp_formants(data, varargin)
%MDP_FORMANTS  - MVIEW dataproc that computes running F1,F2 estimate using ComputeFmts
%
% appends F1, F2

% mkt 02/017

s = data(1).SIGNAL;
sr = data(1).SRATE;
s = ResampleData(s,sr,11025);
fmts = ComputeFmts({s,11025},[],[],[],100);
data(end+1) = data(1);
data(end).NAME = 'F1';
data(end).SRATE = sr;
data(end).SIGNAL = fmts(:,1);
data(end+1) = data(1);
data(end).NAME = 'F2';
data(end).SRATE = sr;
data(end).SIGNAL = fmts(:,2);

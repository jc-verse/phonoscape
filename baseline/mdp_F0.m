function data = mdp_F0(data, varargin)
%MDP_F0  - MVIEW dataproc that computes running F0 estimate using PRAAT
%
% appends F0; assumes audio is DATA(1)
% dependencies:  ComputeF0, PraatF0, ep.praat, copy of Praat.app (or praatcon.exe)

% mkt 02/08

[F0,sr] = ComputeF0(data,[],[80 600],100);
data(end+1) = data(1);
data(end).NAME = 'F0';
data(end).SRATE = sr;
data(end).SIGNAL = F0;

